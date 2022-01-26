import scrapy
from twisted.internet import defer
from twisted.trial.unittest import TestCase
from twisted.internet import reactor

from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging, StreamLogger 
from scrapy.spiders import CrawlSpider, Spider
from scrapy.linkextractors import LinkExtractor

from scrapy.settings import Settings
from scrapy_crawling_bazaar.spiders import CrawlingBazaarSpider, CrawlingBazaarCrawlSpider 
from scrapy.spiders import Rule

import sys
import os
import logging
import time 

logger = logging.getLogger('example-crawling-bazaar')
logger.setLevel(logging.INFO)

configure_logging(install_root_handler=False)
logging.basicConfig(
    filename='run.log',
    filemode = 'w',
    format='%(levelname)s: %(message)s',
    level=logging.INFO
)

#NOTE,NOTE,NOTE 
gcb_path = "/home/wyong/scrapy-crawling-bazaar/example-project/gcb" 

def get_gcb_api_url(repo) :
    try: 
        with open( repo + "/api", 'r')  as f :
            apistring = f.read()
            port = apistring.rsplit("/", 1)[-1]
            return "http://127.0.0.1:" +  port + "/api"
    except IOError:
        return "http://127.0.0.1:3343/api"


class ClientSpider(CrawlSpider):
    name = 'client'
    start_urls = ['http://localhost/index.html']
    
    logger.info("client init...") 

    link_extractor = LinkExtractor(#allow_domains = allowed_domains, 
                                    canonicalize=True, unique=True )

    #for scrapy_link_filter
    extract_rules = { "allow":"/api/frontera/.*",
                      "deny_domains": ["localhost"], 
                    }

    custom_settings = {
        'DOWNLOADER_MIDDLEWARES':{ 'scrapy_link_filter.middleware.LinkFilterMiddleware': 50,
                                   'scrapy_crawling_bazaar.redirect_middleware.RedirectMiddleware': 100,
                                 },
        'LINK_FILTER_MIDDLEWARE_DEBUG' : True,
        'USER_AGENT' : 'scrapy_crawling_bazaar (+https://github.com/siegfried415/scrapy_crawling_bazaar)',

    }

    def __init__(self, name=None, *args, **kwargs):
        logger.info("ClientSpider, __init__ called!" ) 
        super(ClientSpider, self).__init__(*args, **kwargs) 
        self.name = name 

    def parse(self, response):
        #logger.info("ClientSpider, parse, body = {body}".format(body=response.body))
        #yield {'body' : response.body } 

        for h1 in response.xpath('//h1').extract():
            #assert h1 == "<h1>Welcome!</h1>"
            yield {"title": h1}

        for link in self.link_extractor.extract_links(response):
            logger.info("client, parse, find a url={url}".format(url=link.url))
            yield scrapy.Request(link.url, callback=self.parse)


class CrawlerSpider(CrawlingBazaarCrawlSpider):
    name = 'crawler'
    logger.info("%s init...", name) 

    allowed_domains = ["localhost"]
    link_extractor = LinkExtractor(#allow_domains = allowed_domains, 
                                    canonicalize=True, unique=True )

    custom_settings = { 
        'SPIDER_MIDDLEWARES' : { 'scrapy_crawling_bazaar.spidermiddleware.SpiderMiddleware': 0 },

        'USER_AGENT' : 'scrapy_crawling_bazaar (+https://github.com/siegfried415/scrapy_crawling_bazaar)',

    }

    def __init__(self, name=None, *args, **kwargs):
        logger.info("CrawlerSpider, __init__ called!" ) 
        super(CrawlerSpider, self).__init__(*args, **kwargs) 
        self.name = name 

    def parse(self, response):
        logger.info("[{name}], parse, body = {body}".format(name=self.name, body=response.body))
	
        for link in self.link_extractor.extract_links(response):
            logger.info("[{}], parse, find a url={url}".format(name=self.name, url=link.url))
            yield scrapy.Request(link.url, callback=self.parse)

def crawl(runner, cls, name, repo_name ) :
        runner.settings['GCB_API_URL'] = get_gcb_api_url(repo_name )
        #runner.settings.update({
        #    'GCB_API_URL' : get_gcb_api_url(repo_name )
        #})
        crawler = runner.create_crawler(cls)
        runner.crawl(crawler, name=name  ) 

if __name__ == "__main__": 
        runner=CrawlerRunner()
        for i in range(0, 10): 
            crawl(runner, CrawlerSpider, "crawler{}".format(i), "{}/node_miner_{}".format(gcb_path,i))
        crawl(runner, ClientSpider, "client", "{}/node_c".format(gcb_path))

        d = runner.join()
        d.addBoth(lambda _: reactor.stop())

        # the script will block here until ClientCrawler are finished
        reactor.run() 

