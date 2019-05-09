from webpage import WebPage
from time import sleep
import re
import csv

class ImageCrawl:

    def __enter__(self):
        return self

    def __init__(self):
        self.urlDict={
            'bing_img':'https://www.bing.com/images/search?q=',
                 
        }
        self.xpathDict={
            'bing_img':{
                          'input_xpath':"//input[@class='b_searchbox']",
                          'submit_search':"//input[@id='sb_form_go']",
                        },
            'duckduckgo_img':"//input[@class='search__input--adv js-search-input']",
        }
        self.w=WebPage(url=None,browser='chrome')
    
    def startCrawl(self):
        keyword= lambda string : string.replace(' ','+')
        keyword_list=[]
        with open('keywordlist.csv','r') as a:
            reader=csv.reader(a,delimiter=',')
            for r in reader:
                for text in r:
                    keyword_list.append(keyword(text))
        for key in self.urlDict:
            self.w.driver.get(self.urlDict[key])
            print(self.xpathDict[key]) 
            input_field = self.w.driver.find_element_by_xpath(self.xpathDict[key]['input_xpath'])
            input_field.send_keys("Hispanic male")
            self.w.click_element(self.xpathDict[key]['submit_search'])
            sleep(5)
    
    def __exit__(self,exception_type, exception_value, traceback):
        print("quiting driver.................")
        self.w.driver.quit()

if __name__=='__main__':
    ImageCrawl().startCrawl()
