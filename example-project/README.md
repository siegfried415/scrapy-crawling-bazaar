
example-crawling-bazaar

------------------------------------------------
example-crawlinb-bazaar是一个使用scrapy-crawling-bazaar中提供的Spider Class和Middlewares制作的去中心化爬虫的例子，为了运行该例子，需要进行如下步骤：

1) 配置http服务器
为了简化安装和设置，我们使用[simple-mock-server](https://github.com/jonathadv/simple-mock-server)作为http服务器,该服务器非常简单，无需使用pip install安装即可使用。

```shell
~/simple-mock-server/src/server.py -f ./mock-server/mock-server.json
```

2) 启动gcb进程
在example-project目录下面，提供了一个do-start-gcb.sh脚本，在该脚本中，定义启动gcb的函数StartDaemon，该函数包含两个参数，一个是repo路径，一个是角色：

```bash
StartDaemon()
{
        echo "start $2 daemon with repo $1 and log $1/daemon.log ..."
        gcb --repodir $1 --log-level debug --role $2 daemon > "$1/daemon.log" 2>&1
        sleep 5
}
```

然后，就可以启动一个包括一个Leader和两个Follower的Presbyterian网络：
```bash 
StartDaemon "./gcb/node_0"  "Leader" &
StartDaemon "./gcb/node_1"  "Follower" &
StartDaemon "./gcb/node_2"  "Follower" &
```

以及，启动包含10个Crawler Miner的爬虫网络：

```bash
sleep 5
for i in 0 1 2 3 4 5 6 7 8 9
do
        StartDaemon "./gcb/node_miner_$i"  "Miner" &
done
```

最后，启动Client 节点：

```bash
StartDaemon "./gcb/node_c" "Client" &
```

3) 启动Scrapy爬虫
每个Crawler Miner都要启动一个运行CrawlerSpider类的Scrapy实例, 这个CrawlerSpider类是从CrawlingBazaarCrawlSpider派生的爬虫类，这个爬虫类中不包含start_urls，这意味着CrawlerSpider只是被动地等待go-crawling-bazaar网络中派发的url request，而没有自己特有的爬取目标。

为了在一个进程中启动多个爬虫，我们使用了Scrapy提供的CrawlerRunner:

```python
def crawl(runner, cls, name, repo_name ) :
    runner.settings['GCB_API_URL'] = get_gcb_api_url(repo_name )
    crawler = runner.create_crawler(cls)
    runner.crawl(crawler, name=name  )

if __name__ == "__main__":
    runner=CrawlerRunner()
    gcb_path = os.path.abspath(os.path.join(os.getcwd(), "gcb"))
    for i in range(0, 10):
        crawl(runner, CrawlerSpider, "crawler{}".format(i), "{}/node_miner_{}".format(gcb_path,i))

    crawl(runner, ClientSpider, "client", "{}/node_c".format(gcb_path))

    d = runner.join()
    d.addBoth(lambda _: reactor.stop())

    # the script will block here until ClientCrawler are finished
    reactor.run()
```

和上面的CrawlerSpider不同，Client则只要启动一个Scrapy中提供的普通的CrawlSpider类就可以了，为了模拟无法爬取的情况，我们使用了scrapy-link-filter来过滤掉对start_urls的访问，这样才能将该url请求传递给Crawler节点，由Crawler实现爬取之后，再将结果返回给Client：

```python
    start_urls = ['http://localhost/index.html']
    extract_rules = { "allow":"/api/frontera/.*",
                      "deny_domains": ["localhost"],
                    }

    custom_settings = {
        'DOWNLOADER_MIDDLEWARES':{ 'scrapy_link_filter.middleware.LinkFilterMiddleware': 50 },
        'LINK_FILTER_MIDDLEWARE_DEBUG' : True,
    }

```

全部爬取过程都记录到run.log之中，可以通过run.log来确认爬取过程是否成功。
