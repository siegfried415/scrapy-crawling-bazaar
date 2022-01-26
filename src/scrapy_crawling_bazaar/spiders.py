from scrapy import signals
from scrapy.exceptions import DontCloseSpider, IgnoreRequest
from scrapy.spiders import Spider, CrawlSpider
from scrapy.http import Request


from scrapy.utils.misc import load_object

from twisted.internet import reactor
from twisted.internet import defer
import treq 
import json 

import logging
logger = logging.getLogger(__name__)

class CrawlingBazaarMixin(object):
    """Mixin class to implement reading urls from a redis queue."""


    def start_requests(self):
        """Returns a batch of start requests from redis."""
        #return self.next_requests()

        '''
        urls = yield treq.get(self.gcb_api_url + '/bidding/get') 
        for url in urls:
            yield Request(url,dont_filter=False) 
        '''
        return [Request(url, dont_filter=False) for url in self.start_urls]

    def setup_spider(self, crawler=None):
        """Setup redis connection and idle signal.

        This should be called after the spider has set its crawler object.
        """
        #if self.server is not None:
        #    return

        logger.info("[%s] setup_spider called...", self.name)
        if crawler is None:
            # We allow optional crawler argument to keep backwards
            # compatibility.
            # XXX: Raise a deprecation warning.
            crawler = getattr(self, 'crawler', None)

        if crawler is None:
            raise ValueError("crawler is required")

        settings = crawler.settings

        self.gcb_api_url = settings.get('GCB_API_URL', 'http://127.0.0.1:3453' )
        logger.info("[%s] setup_spider , self.gcb_api_url = %s", self.name,  self.gcb_api_url )

        # The idle signal is called when the spider has no requests left,
        # that's when we will schedule new requests from redis queue
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)


    @defer.inlineCallbacks 
    def schedule_next_requests(self):
        logger.info("[%s] schedule_next_requests fetch bidding request from %s...", self.name, self.gcb_api_url + '/bidding/get'  )

        biddings_request = yield treq.get(self.gcb_api_url + '/bidding/get') 
        logger.info("[%s] schedule_next_requests, get bidding request=%s", self.name, biddings_request ) 

        biddings_json = yield biddings_request.json()
        logger.info("[%s] schedule_next_requests, bidding requests json=%s", self.name, biddings_json ) 

        if biddings_json :
            for bidding in biddings_json :
                if 'Url' in bidding and bidding['Url'] != '' : 
                    logger.info("[%s] get bidding request(%s) from crawling bazaar", self.name, bidding['Url'])

                    req = Request(bidding['Url'], dont_filter=False, callback=self.parse ) 
                    req.meta['Probability'] = bidding['Probability']  

                    self.crawler.engine.crawl(req, spider=self)


    def spider_idle(self):
        """Schedules a request if available, otherwise waits."""
        # XXX: Handle a sentinel to close the spider.
        #self.schedule_next_requests()

        #call schedule_next_requests after 5 seconds, wyong, 20180605 
        reactor.callLater(5, self.schedule_next_requests)

        raise DontCloseSpider


class CrawlingBazaarSpider(CrawlingBazaarMixin, Spider):
    @classmethod
    def from_crawler(self, crawler, *args, **kwargs):
        logger.info("CrawlingBazaarSpider from_crawler called...", )
        obj = super(CrawlingBazaarSpider, self).from_crawler(crawler, *args, **kwargs)
        obj.setup_spider(crawler)
        return obj


class CrawlingBazaarCrawlSpider(CrawlingBazaarMixin, CrawlSpider):
    @classmethod
    def from_crawler(self, crawler, *args, **kwargs):
        logger.info("CrawlingBazaarCrawlSpider from_crawler called...", )
        obj = super(CrawlingBazaarCrawlSpider, self).from_crawler(crawler, *args, **kwargs)
        obj.setup_spider(crawler)
        return obj
