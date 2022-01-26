from io import BytesIO, StringIO 

#wyong, 20200317
#import pickle 

from scrapy.http import Request
import json

from twisted.internet import defer
import treq 
#from . import multipart 

import logging
logger = logging.getLogger(__name__)

class SpiderMiddleware(object):

    def __init__(self, settings):
        self.gcb_api_url = settings.get('GCB_API_URL', 'http://127.0.0.1:3453')

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    @defer.inlineCallbacks 
    def process_start_requests(self, start_requests, spider):
        logger.info("[%s] process_start_requests", spider.name )
        urls = []
        for request in start_requests:
            logger.info("[%s] push url request (%s) to crawling bazaar", spider.name,  request.url )
            urls.append({'Url':request.url, 'Probability':1.0} )

        if len(urls) > 0 : 
            yield treq.get( self.gcb_api_url + '/urlrequest/put?arg=' 
                                           + json.dumps({'Url': "", 'Probability':0.0 }, ensure_ascii=False) 
                                           + '&arg='
                                           + json.dumps(urls, ensure_ascii=False))

        return []


    @defer.inlineCallbacks 
    def process_spider_output(self, response, result, spider):
        #save status, headers as well as body
        jresponse =json.dumps({'Status': response.status, 
                               #todo
                               #'Headers': headers, 
                               'Body':response.body.decode(response.encoding)  
                              }, ensure_ascii=False) 
        logger.info("[%s] write page content (%s) to crawling bazaar(%s)", spider.name,  jresponse, self.gcb_api_url + '/dag/import' )

        resp = yield treq.post(self.gcb_api_url + '/dag/import', files={'file': BytesIO(jresponse.encode('utf-8'))})

        res = yield resp.json()
        logger.info("[%s] result = %s", spider.name, res ) 
        logger.info("[%s] get cid(%s) and hash(%s) for url(%s)" , spider.name, res['Cid']['/'], res['Hash'],  response.url)

        yield treq.get( self.gcb_api_url + '/bid/put?arg=' 
                                           + response.url
                                           + "&arg="  + res['Cid']['/']) 

        #logger.info("[%s] page(%s) has been crawled completed!" , spider.name , response.url )

        links = []
        for element in result:
            if isinstance(element, Request):  
                logger.info("[%s] push url request (%s) to crawling bazaar", spider.name,  element.url )
                links.append({'Url':element.url, 'Probability':0.0} )
            else:
                yield element

        if links:
            logger.info("[%s] push url(%s) 's children urls(%s) to crawling bazaar", spider.name,  response.request.url, json.dumps(links, ensure_ascii=False) )
            yield treq.get( self.gcb_api_url + '/bidding/put?arg='
                                           + json.dumps({'Url': response.request.url, 'Probability': response.request.meta.get('Probability','0.5')}, ensure_ascii=False) 
                                           + '&arg=' 
                                           + json.dumps(links, ensure_ascii=False))

            #self.stats.inc_value('scrapyfrontera/links_extracted_count', len(links))


