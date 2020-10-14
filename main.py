# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 14:20:02 2020

@author: aliha
@twitter: rockingAli5 
"""

import time
import pandas as pd
import json
from bs4 import BeautifulSoup as soup
from tqdm import trange


from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException




def getLeagueLinks(main_url):
    
    driver = webdriver.Chrome('chromedriver.exe')
    driver.minimize_window()
        
    main = driver.get(main_url)
    leagues = []
    for i in range(22):
        league = driver.find_element_by_xpath('//*[@id="popular-tournaments-list"]/li['+str(i+1)+']/a').get_attribute('href')
        leagues.append(league)
    driver.close()
    return leagues


        
def getMatchLinks(comp_url, main_url):
    
    driver = webdriver.Chrome('chromedriver.exe')
    
    teams = []
    comp = driver.get(comp_url)
    season = driver.find_element_by_xpath('//*[@id="seasons"]/option[2]').click()
    for i in range(20):
        team = driver.find_element_by_xpath('//*[@id="standings-17702-content"]/tr['+str(i+1)+']/td[1]/a').text
        teams.append(team)
    time.sleep(5)
    fixtures_page = driver.find_element_by_xpath('//*[@id="link-fixtures"]').click()
    time.sleep(5)
    date_config_btn = driver.find_element_by_xpath('//*[@id="date-config-toggle-button"]').click()
    time.sleep(5)
    year1 = driver.find_element_by_xpath('//*[@id="date-config"]/div[1]/div/table/tbody/tr/td[1]/div/table/tbody/tr[1]/td').click()
    selectable_months = driver.find_element_by_xpath('//*[@id="date-config"]/div[1]/div/table/tbody/tr/td[2]/div/table').find_elements_by_class_name("selectable")
    
    n_months = len(selectable_months)
    
    year2 = driver.find_element_by_xpath('//*[@id="date-config"]/div[1]/div/table/tbody/tr/td[1]/div/table/tbody/tr[2]/td').click()
    selectable_months = driver.find_element_by_xpath('//*[@id="date-config"]/div[1]/div/table/tbody/tr/td[2]/div/table').find_elements_by_class_name("selectable")
    
    n_months += len(selectable_months)
    date_config_btn = driver.find_element_by_xpath('//*[@id="date-config-toggle-button"]').click()
    
    #for month_element in selectable_months:
    match_links = []
    
    for i in range(n_months):
        time.sleep(2)
        fixtures_table = driver.find_element_by_xpath('//*[@id="tournament-fixture"]')
        fixtures_table = fixtures_table.get_attribute('innerHTML')
        fixtures_table = soup(fixtures_table, features="lxml")
        table_rows1 = fixtures_table.find_all("div", {"class":"divtable-row col12-lg-12 col12-m-12 col12-s-12 col12-xs-12"})    
        table_rows2 = fixtures_table.find_all("div", {"class":"divtable-row col12-lg-12 col12-m-12 col12-s-12 col12-xs-12 alt"})
        table_rows = table_rows1+table_rows2
        links = []
        links = [main_url+row.find("a", {"class":"result-1 rc"}).get("href") for row in table_rows]
        for link in links:
            match_links.append(link)
        previous_month = driver.find_element_by_xpath('//*[@id="date-controller"]/a[1]').click()
    if len(match_links) != 380:
        fixtures_table = driver.find_element_by_xpath('//*[@id="tournament-fixture"]')
        fixtures_table = fixtures_table.get_attribute('innerHTML')
        fixtures_table = soup(fixtures_table)
        table_rows1 = fixtures_table.find_all("div", {"class":"divtable-row col12-lg-12 col12-m-12 col12-s-12 col12-xs-12"})    
        table_rows2 = fixtures_table.find_all("div", {"class":"divtable-row col12-lg-12 col12-m-12 col12-s-12 col12-xs-12 alt"})
        table_rows = table_rows1+table_rows2
        links = []
        links = [main_url+row.find("a", {"class":"result-1 rc"}).get("href") for row in table_rows]
        for link in links:
            match_links.append(link)
    
    match_links = list(dict.fromkeys(match_links))
    driver.close()
    return teams, match_links

def getTeamLinks(team, match_links):
    team = team.split()
    team_links = []
    for link in match_links:
        if len(team) == 1:
            if team[0] in link:
                team_links.append(link)
        else:
            if team[0]+'-'+team[1] in link:
                team_links.append(link)
                
    return team_links



def getTeamData(team_links):
    matches = []
    
    driver = webdriver.Chrome('chromedriver.exe')
    driver.minimize_window()
    
    for i in trange(len(team_links), desc='Single loop'):
        driver.get(team_links[i])
        time.sleep(2)
        element = driver.find_element_by_xpath('//*[@id="layout-wrapper"]/script[1]')
        script_content = element.get_attribute('innerHTML')
        script_ls = script_content.split(sep="  ")
        script_ls = list(filter(None, script_ls))
        script_ls = [name for name in script_ls if name.strip()]
        script_ls_mod = []
        keys = []
        for item in script_ls:
            if "}" in item:
                item = item.replace(";", "")
                script_ls_mod.append(item[item.index("{"):])
                keys.append(item.split()[1])
            else:
                item = item.replace(";", "")
                script_ls_mod.append(int(''.join(filter(str.isdigit, item))))
                keys.append(item.split()[1])
        
        match_data = json.loads(script_ls_mod[0]) 
        for key, item in zip(keys[1:], script_ls_mod[1:]):
            if type(item) == str:
                match_data[key] = json.loads(item)
            else:
                match_data[key] = item
    
        matches.append(match_data)
        
    driver.close()
    
    return matches




def getMatchData(driver, url):
    driver.get(url)

    element = driver.find_element_by_xpath('//*[@id="layout-wrapper"]/script[1]')
    script_content = element.get_attribute('innerHTML')
    script_ls = script_content.split(sep="  ")
    script_ls = list(filter(None, script_ls))
    script_ls = [name for name in script_ls if name.strip()]
    script_ls_mod = []
    keys = []
    for item in script_ls:
        if "}" in item:
            item = item.replace(";", "")
            script_ls_mod.append(item[item.index("{"):])
            keys.append(item.split()[1])
        else:
            item = item.replace(";", "")
            script_ls_mod.append(int(''.join(filter(str.isdigit, item))))
            keys.append(item.split()[1])
    
    match_data = json.loads(script_ls_mod[0]) 
    for key, item in zip(keys[1:], script_ls_mod[1:]):
        if type(item) == str:
            match_data[key] = json.loads(item)
        else:
            match_data[key] = item
    driver.close()
    return match_data





def createEventsDF(matches):
    if type(matches) == dict:
        events = matches['events']
        for event in events:
            event.update({'matchId' : matches['matchId'],
                         'startDate' : matches['startDate'],
                         'startTime' : matches['startTime'],
                         'score' : matches['score'],
                         'ftScore' : matches['ftScore'],
                         'htScore' : matches['htScore'],
                         'etScore' : matches['etScore'],
                         'venueName' : matches['venueName'],
                         'maxMinute' : matches['maxMinute']})
        events_df = pd.DataFrame(events)
        return events_df
    else:
        for i in trange(len(matches), desc='Single loop'):
            events = matches[i]['events']
            for event in events:
                event.update({'matchId' : matches[i]['matchId'],
                             'startDate' : matches[i]['startDate'],
                             'startTime' : matches[i]['startTime'],
                             'score' : matches[i]['score'],
                             'ftScore' : matches[i]['ftScore'],
                             'htScore' : matches[i]['htScore'],
                             'etScore' : matches[i]['etScore'],
                             'venueName' : matches[i]['venueName'],
                             'maxMinute' : matches[i]['maxMinute']})
        events_ls = []
        for match in matches:
            match_events = match['events']
            match_events_df = pd.DataFrame(match_events)
            events_ls.append(match_events_df)
                
        events_df = pd.concat(events_ls)
        return events_df
    


def createMatchesDF(data):
    columns_req_ls = ['matchId', 'attendance', 'venueName', 'startTime', 'startDate',
                      'score', 'home', 'away', 'referee']
    matches_df = pd.DataFrame(columns=columns_req_ls)
    if type(data) == dict:
        matches_dict = dict([(key,val) for key,val in data.items() if key in columns_req_ls])
        matches_df = matches_df.append(matches_dict, ignore_index=True)
    else:
        for match in data:
            matches_dict = dict([(key,val) for key,val in match.items() if key in columns_req_ls])
            matches_df = matches_df.append(matches_dict, ignore_index=True)
    
    matches_df = matches_df.set_index('matchId')        
    return matches_df


























