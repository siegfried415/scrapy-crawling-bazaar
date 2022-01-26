scrapy-crawling-bazaar

--------------------------------------------------------

scrapy-crawling-bazaar是一个基于Scrapy和[go-crawling-bazaar](https://github.com/siegfried415/go-crawling-bazaar) 实现的去中心爬虫平台，使用该平台，爬虫开发者可以将自己的爬虫改造成一个去中心化爬虫，继而可以使用crawling bazaar爬虫网络来进行大规模的分布式爬取。

传统的大规模爬虫开发者为了提高爬取效率、并对抗网站的反爬取策略，通常使用由多个节点构成的分布式爬取模式，比如，爬虫开发者要么自己部署的大量爬虫节点（如Scrapy-redis），要么使用付费的proxy-pool作为分布式爬取节点，或者使用特定厂商（Scrapinghub）提供的云爬取服务（比如scrapy-frontera）, 但无论使用哪种策略都需要支付高昂的部署成本，如何降低爬取成本，就成了大规模爬虫开发者所必须要解决的首要问题。

为了降低部署成本，我们开发了去中心化爬虫市场[go-crawling-bazaar](https://github.com/siegfried415/go-crawling-bazaar)，scrapy-crawling-bazaar中的爬虫是由世界上多个拥有拥有宽带资源和闲置存储能力的开发者提供的，所有这些爬虫构成一个去中心化的爬虫网络。爬虫开发者可以通过支付一定的Token来让其他的爬虫节点来运行自己的爬取任务，这些提供服务的爬虫节点（我们称之为Crawler）通过为客户爬虫（我们称之为Client）提供服务来赚取Token，以此形成一个互惠互利的爬取市场。

在本质上，go-crawling-bazaar是一个全局的frontera，它负责维护一个url request队列，当爬虫闲置下来后，就可以从该队列头部获得下一个url爬取任务，以及，当爬虫完成爬取任务之后分析页面中的links之后将这些links插入到队列尾部。当然一个完整的爬虫仍然需要完成具体的爬取、分析和存储等任务，这就需要依赖于一个能够跟go-crawling-bazaar打交道的爬虫框架，考虑到Scrapy在爬虫领域的流行程度，我们在Scrapy-crawling-bazaar中提供了一些修改的类（比如RedirectMiddleware、CrawlingBazaarCrawlSpider和SpiderMiddleware），用以替换Scrapy的原始实现，这样，就可以帮助Scrapy爬虫作者快速地实现一个去中心化爬虫。

Client爬虫的改造是非常简单的，只需要在DOWNLOADER_MIDDLEWARES中使用RedirectMiddleware就可以了，该Middleware的作用是当目标url无法访问时，将到crawling-bazaar中查询是否该url已经被某些Crawler爬取并保存了，如有是，则直接从这些Crawler那里进行下载，否则，则向crawling-bazaar发出一条爬取请求，然后等待被选中的Crawler进行爬取:
```python
class ClientSpider(CrawlSpider):
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES':{ 'scrapy_crawling_bazaar.redirect_middleware.RedirectMiddleware' :100 },
    }
}
```

而对于那些提供下载服务的Crawler来说，则需要基于Scrapy-crawling-bazaar中提供的CrawlingBazaarCrawlSpider来定义一个爬虫，该爬虫通过不断读取go-crawling-bazaar来获取下一个待爬取的url任务，同时，需要额外使用`SpiderMiddleware`的SPIDER_MIDDLEWARES，该SPIDER_MIDDLEWARE的作用是在分析出links之后，将links传递给go-crawling-bazaar，使得其他Crawler得到爬取它们的机会:
```python
class CrawlerSpider(CrawlingBazaarCrawlSpider):
    custom_settings = { 
        'SPIDER_MIDDLEWARES' : { 'scrapy_crawling_bazaar.spidermiddleware.SpiderMiddleware': 0 },

    }
}
```

由于Crawler没有自己的爬取目标，所以在Crawler Spider中无需设置start_urls。具体例子可以参考 [example-crawling-bazaar](https://github.com/siegfried415/scrapy-crawling-bazaar/tree/main/example-project)。
