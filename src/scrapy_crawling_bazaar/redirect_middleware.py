
from twisted.internet import defer
import treq 
import json 

from scrapy.http import HtmlResponse
from scrapy.downloadermiddlewares.redirect import BaseRedirectMiddleware as BaseRedirectMiddleware
from scrapy.utils.response import response_status_message

from twisted.internet import task, reactor
from twisted.internet.error import TimeoutError, DNSLookupError, \
        ConnectionRefusedError, ConnectionDone, ConnectError, \
        ConnectionLost, TCPTimedOutError
from twisted.web.client import ResponseFailed

from scrapy.utils.response import response_status_message
from scrapy.core.downloader.handlers.http11 import TunnelError
from scrapy.utils.python import global_object_name

from scrapy.exceptions import IgnoreRequest, NotConfigured, DontCloseSpider 

import logging
logger = logging.getLogger(__name__)


class RedirectMiddleware(BaseRedirectMiddleware):
    def __init__(self, settings):
        self.gcb_api_url = settings.get('GCB_API_URL', 'http://127.0.0.1:3453')
        self.redirect_http_codes = set(int(x) for x in settings.getlist('REDIRECT_HTTP_CODES'))
        self.max_redirect_times = 2 
        self.priority_adjust = 0 

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_response(self, request, response, spider):
        logger.info("[%s] process_response", spider.name )
        if request.meta.get('dont_redirect', False) or request.method == 'HEAD' or not isinstance(response, HtmlResponse) :
            return response
	
        if response.status in self.redirect_http_codes:
            reason = response_status_message(response.status)
            return self._get_cid(request, reason, spider) or response

        return response

    def process_exception(self, request, exception, spider):
        logger.info("[%s] process_exception called, url=%s", spider.name, request.url )
        reason = self._get_exception_code(exception)
        return self._get_cid('', request, reason, spider, 5 )  
 

    def _get_cid(self, result, request, reason, spider, count ): 
        logger.info("[%s] _get_cid called, request url=%s", spider.name, request.url )
        #look for WebUrl contract to find page_hash of requested url
        d = treq.get( self.gcb_api_url + '/urlgraph/get-page-cid-by-url?arg=' + request.url ) 
        d.addCallback(self._parse_cid, request, reason, spider, count )
        return d

    def _get_cid_later(self, result, request, reason, spider, count ):
        logger.info("[%s] _get_cid_later called for %s", spider.name, request.url )
        return task.deferLater(reactor, 15, self._get_cid, result, request, reason, spider, count )
            

    def _parse_cid(self, result, request, reason, spider, count):
        logger.info("[%s] _parse_cid called, url=%s, result=%s" , spider.name, request.url, result)
        d = result.json()
        d.addCallback(self._process_cid, request, reason, spider, count)
        return d 


    def _process_cid(self, result, request, reason, spider, count):
        logger.info("[%s] _process_cid called, result=%s" , spider.name,  result )
        if result and '/' in result :  
            logger.info("[%s] _process_cid, found cid=%s for %s, call _get_dag..." , spider.name, result['/'], request.url )
            return self._get_dag(result['/'], request, reason, spider)
        else:
            logger.info("[%s] _process_cid, not found cid, push url requests(%s) with parent(%s) to crawling market, then call _get_cid_later...", spider.name, request.url , request.headers.get('Referer', "").decode("utf-8"))

            if count > 1 : 
                d = treq.get( self.gcb_api_url + '/urlrequest/put?arg='
                                           + json.dumps({'Url': request.headers.get('Referer', "").decode("utf-8"), 'Probability': 0.0}, ensure_ascii=False)

                                           + '&arg=' 
                                           + json.dumps([{'Url':request.url, 'Probability':1.0}], ensure_ascii=False))

                d.addCallback(self._get_cid_later, request, reason, spider, count -1  ) 
                return d 
            else :
                raise ResponseFailed("can't get url from crawling bazaar" )

    def _get_dag(self, cid, request, reason, spider):
        logger.info("[%s] _get_dag called, url=%s", spider.name, request.url)
        d = treq.get( self.gcb_api_url + 
                      '/dag/cat?arg=' + json.dumps(request.headers.get('Referer', "").decode("utf-8"), ensure_ascii=False) + 
                      '&arg=' + json.dumps(request.url , ensure_ascii=False) + 
                      '&arg=' + cid ) 

        d.addCallback(self._parse_dag, request, reason, spider ) 
        return d 

    def _parse_dag(self, result, request, reason, spider) :
        logger.info("[%s] _parse_dag called, url=%s, result=%s ", spider.name, request.url, result )
        d = result.json()
        d.addCallback(self._build_response, request, reason, spider)
        return d 

    def _build_response(self, result, request, reason, spider) :
        # convert json to dict. 
        result = json.loads(result) 
        logger.info("[%s] _build_response called, url=%s, status=%s, body=%s", spider.name, request.url, result["Status"], result["Body"] )
        request.meta['dont_redirect'] = True 
        return HtmlResponse(url=request.url, 
                               request = request, 
                               status=result["Status"], 
                               #headers=result["Headers"], 
                               body=result["Body"].encode('utf-8'))

    def _get_exception_code(self, exception):
        try:
            return exception.__class__.__name__
        except:
            return '?'

