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
import re 
from collections import OrderedDict


from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

import sys
# add path to the "LaurieOnTracking-master" repo folder on your system
sys.path.append("../../../Football Data Analysis/LaurieOnTracking-master")
import Metrica_EPV as mepv
import numpy as np


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

    # get script data from page source
    script_content = driver.find_element_by_xpath('//*[@id="layout-wrapper"]/script[1]').get_attribute('innerHTML')


    # clean script content
    script_content = re.sub(r"[\n\t]*", "", script_content)
    script_content = script_content[script_content.index("matchId"):script_content.rindex("}")]


    # this will give script content in list form 
    script_content_list = list(filter(None, script_content.strip().split(',            ')))
    metadata = script_content_list.pop(1) 


    # string format to json format
    match_data = json.loads(metadata[metadata.index('{'):])
    keys = [item[:item.index(':')].strip() for item in script_content_list]
    values = [item[item.index(':')+1:].strip() for item in script_content_list]
    for key,val in zip(keys, values):
        match_data[key] = json.loads(val)


    # get other details about the match
    region = driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/span[1]').text
    league = driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/a').text.split(' - ')[0]
    season = driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/a').text.split(' - ')[1]
    if len(driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/a').text.split(' - ')) == 2:
        competition_type = 'League'
        competition_stage = ''
    elif len(driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/a').text.split(' - ')) == 3:
        competition_type = 'Knock Out'
        competition_stage = driver.find_element_by_xpath('//*[@id="breadcrumb-nav"]/a').text.split(' - ')[-1]
    else:
        print('Getting more than 3 types of information about the competition.')

    match_data['region'] = region
    match_data['league'] = league
    match_data['season'] = season
    match_data['competitionType'] = competition_type
    match_data['competitionStage'] = competition_stage


    # sort match_data dictionary alphabetically
    match_data = OrderedDict(sorted(match_data.items()))
    match_data = dict(match_data)
    print('Region: {}, League: {}, Season: {}, Match Id: {}'.format(region, league, season, match_data['matchId']))
    
    
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









def to_metric_coordinates_from_whoscored(data,field_dimen=(106.,68.) ):
    '''
    Convert positions from Whoscored units to meters (with origin at centre circle)
    '''
    x_columns = [c for c in data.columns if c[-1].lower()=='x'][:2]
    y_columns = [c for c in data.columns if c[-1].lower()=='y'][:2]
    x_columns_mod = [c+'_metrica' for c in x_columns]
    y_columns_mod = [c+'_metrica' for c in y_columns]
    data[x_columns_mod] = (data[x_columns]/100*106)-53
    data[y_columns_mod] = (data[y_columns]/100*68)-34
    #data[x_columns_mod] = data[x_columns]/100*1.06
    #data[y_columns_mod] = data[y_columns]/100*1.06
    #data[x_columns_mod] = ( data[x_columns_mod]-0.5 ) * field_dimen[0]
    #data[y_columns_mod] = ( data[y_columns_mod]-0.5 ) * field_dimen[1]
    
    return data




def addEpvToDataFrame(data,EPV):
    EPV_start = []
    EPV_end = []
    EPV_difference = []
    for i,row in data.iterrows():
        if row['type']['displayName'] == 'Pass' and row['outcomeType']['value'] == 1:
            start_pos = (row['x_metrica'], row['y_metrica'])
            start_epv = mepv.get_EPV_at_location(start_pos,EPV,attack_direction=1)
            EPV_start.append(start_epv)
            
            end_pos = (row['endX_metrica'], row['endY_metrica'])
            end_epv = mepv.get_EPV_at_location(end_pos,EPV,attack_direction=1)
            EPV_end.append(end_epv)
            
            diff = end_epv - start_epv
            EPV_difference.append(diff)
            
        else:
            EPV_start.append(np.nan)
            EPV_end.append(np.nan)
            EPV_difference.append(np.nan)
    
    data = data.assign(EPV_start = EPV_start,
                       EPV_end = EPV_end,
                       EPV_difference = EPV_difference)
    return data




















