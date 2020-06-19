# Design Document for Github Mirror

## Context

The github mirror acts as a proxy for the Github API and is used to limit the number of calls to the Github API by serving cached objects to the client whenever possible. This prevents clients from becoming rate limited by exceeding their API quota too quickly.

When a client requests a resource from the mirror, the mirror first looks up the resource in the cache to obtain its [etag](https://developer.github.com/v3/#conditional-requests) (which identifies the version of the resource). If it is found, the mirror includes this etag in a conditional request to the Github API. If cache entry is stale, the mirror will receive the new version of the resource (along with a new etag) which it then caches and serves to the client. However, if the resource has not changed the mirror will receive a [304 Not Modified](https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html) response and will serve the cached object to the client.

## Goals

* Re-design the Github [mirror](#mirror) to reduce the number of Github API requests required to build up the mirror cache with every pod restart (ex: pod failure, deployment, etc.). 

* Specifically, cache rebuilding after a restart should require only one API call per resource per user, so that the number of API calls does not grow linearly in the number of [mirror replicas](#mirror-replica). 

* Minimize latency so that the average mirror [request time](#request-time) does not increase significantly.

## Current solution

The github mirror is deployed in an OpenShift cluster with a replication factor of 3.

Each replica of the github mirror server maintains its own [local in-memory cache](#local-in-memory-cache). The cache is a data structure (Python dictionary) with constant-time lookup. The cache may grow unbounded if the pod continues running and does not restart.

The current design incurs a significant overhead during redeployment as each replica has to build and maintain its own copy of the cache (meaning one API call per resource per replica). This design does not scale well if the number of replicas is increased, as the [hourly quota](https://developer.github.com/v3/#rate-limiting) for Github API requests will quickly be exhausted, causing a hold up for all [clients](#client) depending on this service.

## Proposed solution

### Overview
* Replace each pod's local in-memory cache with a single shared cache for all pods. 

    * The [cache server](#cache-server) should be deployed within the same Open Shift cluster as the Github mirror to reduce the latency associated with requests to the cache.

    * A shared cache should reduce the number of calls to the Github API since each pod will not maintain its own copy of the cache.

    * When the mirror is redeployed, the cache will have to be rebuilt once only, instead of once for *each* replica.

* Use an in-memory key-value store as the shared cache server.

    * The etags returned with each conditional request to the Github API are unique. Therefore etags can be used as a key to store and retreive the results of each API request. 

* The key-value store should meet the following requirements.

    * Highly available, to prevent bottlenecks and minimize latency.
    * Persistent, to prevent loss of all cached information in the case of a pod restart.
    * Weak consistency since we can tolerate stale reads

### Implementation details

* The shared cache will be implemented using a Redis cluster. 

    * Since the goal is to minimize response time, a in-memory key-value is needed. There are several key-value stores that meet the critera, notably [Redis](https://redis.io/) or [Memcached](https://memcached.org/).

    * Memcached has a limit on the size of the object being stored (< 1 MB), however, most of the response objects returned by the API will be small and therefore Memcached or Redis will both work in this regard.

    * The main advantage that Redis has over Memcached is with regards to availability and persistence. [Memcached does not offer replication or persistence](https://docs.aws.amazon.com/AmazonElastiCache/latest/mem-ug/SelectEngine.html), so if the server fails or is restarted, the cache will be lost.

    * Redis offers [persistence](https://redis.io/topics/persistence) using <a name="rdb-files"></a>RDB files which are snapshots of the data written to disk at specifiable intervals. Redis provides more durable persistence using AOF logs but that is not required in this case.

    * Redis can be configured to be highly available. A Redis master can be replicated using two worker nodes, but can replace it in the case of a failover. A Redis sentinel is used to select the replacement node when a master node fails.

    * Redis does not guarantee [strong consistency](https://redis.io/topics/cluster-tutorial#redis-cluster-consistency-guarantees) which is acceptable since any stale cache reads will always be compared against the response from the conditional request, resulting - in the worst case - in an additional request to the Github API as well as unnecessarily replacing the cache entry.

    * Other features of Redis include sharding the cache if it gets too big, as well as the ability to select from a number of cache eviction policies.

* Measuring latency

    * A Prometheus metrics endpoint exists that is used to graph the average latency of the mirror for the 90, 95, 99 percentile. Another metric can be added to show the additional latency created by introducing the Redis cache server.

### Architecture diagram

![](./images/arch.svg)

## Scope

* Backing up the cache is not necessary as long as the cache rebuild time is constant in the size of mirror replicas.

* Project should use free and open source software and not incur an additional cost in terms of licensing fees.

## Acceptance Criteria

* A successful solution will provide a highly available, low latency mirror server, that can be easily scaled from 3 to 100 replicas without being rate limited by the Github API.

* Additional latency due to redesign will not exceed 3 [http request times](http://services.google.com/fh/files/blogs/google_delayexp.pdf).

* User can set up the mirror to use either the per-pod local in-memory cache or the Redis server simply by modifying a configuration file. 

## Extensions

* Create a backup of the cache to avoid unnecessarily rebuilding it in the case or a server/pod failure or redeployment. A simple solution would involve rebuilding the cache from Redis snapshots ([RDB files](#rdb-files)) stored in an external object store (ex: S3).

* To increase availability and to keep the cache from growing too large, sharding can be used to break up the cache into smaller parts stored on separate shards.

* Analyze mirror usage to set suitable cache [expiration](https://redis.io/commands/expire) times.

## Open Questions

* How are results of http requests stored in Redis? Do they need to be serialized?

## Glossary

* <a name="client"></a>**client**: any application making http requests to the mirror.

* <a name="mirror"></a>**mirror**: serves cached data to the client and makes conditional requests to the Github API.

* <a name="mirror-replica"></a>**mirror replica**: replicas of the mirror server, increasing availability, fault tolerance and distributing the load.

* <a name="cache-server"></a>**cache server**: server which caches results of Github API calls by the mirror.

* <a name="local-in-memory-cache"></a>**local in-memory cache**: *in this context*, it refers to each pod's ephermeral cache that is lost when a pods fails, is deleted, restarted or redeployed. Not to be confused with Redis which is often described as an in-memory cache!

* <a name="request-time"></a>**request time**: the time it takes for the client to receive a response to a request made to the mirror server, and this includes the time the mirror takes to make Github API calls and to make requests to the cache. 
