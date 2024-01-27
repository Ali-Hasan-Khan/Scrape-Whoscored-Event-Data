# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 14:20:02 2020

@author: aliha
@twitter: rockingAli5 
"""

import warnings
import time
import pandas as pd
pd.options.mode.chained_assignment = None
import json
from bs4 import BeautifulSoup as soup
import re 
from collections import OrderedDict
import datetime
from datetime import datetime as dt
import itertools
import numpy as np
try:
    from tqdm import trange
except ModuleNotFoundError:
    pass


from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

options = webdriver.ChromeOptions()

options.add_experimental_option('excludeSwitches', ['enable-logging'])


TRANSLATE_DICT = {'Jan': 'Jan',
                 'Feb': 'Feb',
                 'Mac': 'Mar',
                 'Apr': 'Apr',
                 'Mei': 'May',
                 'Jun': 'Jun',
                 'Jul': 'Jul',
                 'Ago': 'Aug',
                 'Sep': 'Sep',
                 'Okt': 'Oct',
                 'Nov': 'Nov',
                 'Des': 'Dec',
                 'Jan': 'Jan',
                 'Feb': 'Feb',
                 'Mar': 'Mar',
                 'Apr': 'Apr',
                 'May': 'May',
                 'Jun': 'Jun',
                 'Jul': 'Jul',
                 'Aug': 'Aug',
                 'Sep': 'Sep',
                 'Oct': 'Oct',
                 'Nov': 'Nov',
                 'Dec': 'Dec'}

main_url = 'https://1xbet.whoscored.com/'



def getLeagueUrls(minimize_window=True):
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    
    if minimize_window:
        driver.minimize_window()
        
    driver.get(main_url)
    league_names = []
    league_urls = []
    n_tournaments = len(soup(driver.find_element(By.ID, 'popular-tournaments-list').get_attribute('innerHTML')).findAll('li'))
    for i in range(n_tournaments):
        league_name = driver.find_element(By.XPATH, '//*[@id="popular-tournaments-list"]/li['+str(i+1)+']/a').text
        league_link = driver.find_element(By.XPATH, '//*[@id="popular-tournaments-list"]/li['+str(i+1)+']/a').get_attribute('href')
        league_names.append(league_name)
        league_urls.append(league_link)
        
    for link in league_urls:
        if 'Russia' in link:
            r_index = league_urls.index(link)
            
    league_names[r_index] = 'Russian Premier League'
    
    leagues = {}
    for name,link in zip(league_names,league_urls):
        leagues[name] = link
    driver.close()
    return leagues


      
def getMatchUrls(comp_urls, competition, season, maximize_window=True):

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    
    if maximize_window:
        driver.maximize_window()
    
    comp_url = comp_urls[competition]
    driver.get(comp_url)
    time.sleep(5)
    
    seasons = driver.find_element(By.XPATH, '//*[@id="seasons"]').get_attribute('innerHTML').split(sep='\n')
    seasons = [i for i in seasons if i]
    
    
    for i in range(1, len(seasons)+1):
        if driver.find_element(By.XPATH, '//*[@id="seasons"]/option['+str(i)+']').text == season:
            driver.find_element(By.XPATH, '//*[@id="seasons"]/option['+str(i)+']').click()
            
            time.sleep(5)
            try:
                stages = driver.find_element(By.XPATH, '//*[@id="stages"]').get_attribute('innerHTML').split(sep='\n')
                stages = [i for i in stages if i]
                
                all_urls = []
            
                for i in range(1, len(stages)+1):
                    if competition == 'Champions League' or competition == 'Europa League':
                        if 'Group Stages' in driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').text or 'Final Stage' in driver.find_element_by_xpath('//*[@id="stages"]/option['+str(i)+']').text:
                            driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').click()
                            time.sleep(5)
                            
                            driver.execute_script("window.scrollTo(0, 400)") 
                            
                            match_urls = getFixtureData(driver)
                            
                            match_urls = getSortedData(match_urls)
                            
                            match_urls2 = [url for url in match_urls if '?' not in url['date'] and '\n' not in url['date']]
                            
                            all_urls += match_urls2
                        else:
                            continue
                    
                    elif competition == 'Major League Soccer':
                        if 'Grp. ' not in driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').text: 
                            driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').click()
                            time.sleep(5)
                        
                            driver.execute_script("window.scrollTo(0, 400)")
                            
                            match_urls = getFixtureData(driver)
                            
                            match_urls = getSortedData(match_urls)
                            
                            match_urls2 = [url for url in match_urls if '?' not in url['date'] and '\n' not in url['date']]
                            
                            all_urls += match_urls2
                        else:
                            continue
                        
                    else:
                        driver.find_element(By.XPATH, '//*[@id="stages"]/option['+str(i)+']').click()
                        time.sleep(5)
                    
                        driver.execute_script("window.scrollTo(0, 400)")
                        
                        match_urls = getFixtureData(driver)
                        
                        match_urls = getSortedData(match_urls)
                        
                        match_urls2 = [url for url in match_urls if '?' not in url['date'] and '\n' not in url['date']]
                        
                        all_urls += match_urls2
                
            except NoSuchElementException:
                all_urls = []
                
                driver.execute_script("window.scrollTo(0, 400)")
                
                match_urls = getFixtureData(driver)
                
                match_urls = getSortedData(match_urls)
                
                match_urls2 = [url for url in match_urls if '?' not in url['date'] and '\n' not in url['date']]
                
                all_urls += match_urls2
            
            
            remove_dup = [dict(t) for t in {tuple(sorted(d.items())) for d in all_urls}]
            all_urls = getSortedData(remove_dup)
            
            driver.close() 
    
            return all_urls
     
    season_names = [re.search(r'\>(.*?)\<',season).group(1) for season in seasons]
    driver.close() 
    print('Seasons available: {}'.format(season_names))
    raise('Season Not Found.')
    




def getTeamUrls(team, match_urls):
    
    team_data = []
    for fixture in match_urls:
        if fixture['home'] == team or fixture['away'] == team:
            team_data.append(fixture)
    team_data = [a[0] for a in itertools.groupby(team_data)]
                
    return team_data


def getMatchesData(match_urls, minimize_window=True):
    
    matches = []
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    if minimize_window:
        driver.minimize_window()
    
    try:
        for i in trange(len(match_urls), desc='Getting Match Data'):
            # recommended to avoid getting blocked by incapsula/imperva bots
            time.sleep(7)
            match_data = getMatchData(driver, main_url+match_urls[i]['url'], display=False, close_window=False)
            matches.append(match_data)
    except NameError:
        print('Recommended: \'pip install tqdm\' for a progress bar while the data gets scraped....')
        time.sleep(7)
        for i in range(len(match_urls)):
            match_data = getMatchData(driver, main_url+match_urls[i]['url'], display=False, close_window=False)
            matches.append(match_data)
    
    driver.close()
    
    return matches




def getFixtureData(driver):

    matches_ls = []
    while True:
        table_rows = driver.find_elements(By.CLASS_NAME, 'divtable-row')
        if len(table_rows) == 0:
            if('is-disabled' in driver.find_element(By.XPATH, '//*[@id="date-controller"]/a[1]').get_attribute('class').split()):
                break
            else:
                driver.find_element(By.XPATH, '//*[@id="date-controller"]/a[1]').click()
        for row in table_rows:
            match_dict = {}
            element = soup(row.get_attribute('innerHTML'), features='lxml')
            link_tag = element.find("a", {"class":"result-1 rc"})
            if type(link_tag) is type(None):
                if type(element.find('span', {'class':'status-1 rc'})) is type(None):
                    date = row.text.split(', ')[-1]
            if type(link_tag) is not type(None):
                match_dict['date'] = date
                match_dict['time'] = element.find('div', {'class':'col12-lg-1 col12-m-1 col12-s-0 col12-xs-0 time divtable-data'}).text
                match_dict['home'] = element.find_all("a", {"class":"team-link"})[0].text
                match_dict['away'] = element.find_all("a", {"class":"team-link"})[1].text
                match_dict['score'] = element.find("a", {"class":"result-1 rc"}).text
                match_dict['url'] = link_tag.get("href")
            matches_ls.append(match_dict)
                
        prev_month = driver.find_element(By.XPATH, '//*[@id="date-controller"]/a[1]').click()
        time.sleep(2)
        if driver.find_element(By.XPATH, '//*[@id="date-controller"]/a[1]').get_attribute('title') == 'No data for previous week':
            table_rows = driver.find_elements(By.CLASS_NAME, 'divtable-row')
            for row in table_rows:
                match_dict = {}
                element = soup(row.get_attribute('innerHTML'), features='lxml')
                link_tag = element.find("a", {"class":"result-1 rc"})
                if type(link_tag) is type(None):
                    if type(element.find('span', {'class':'status-1 rc'})) is type(None):
                        date = row.text.split(', ')[-1]
                if type(link_tag) is not type(None):
                    match_dict['date'] = date
                    match_dict['time'] = element.find('div', {'class':'col12-lg-1 col12-m-1 col12-s-0 col12-xs-0 time divtable-data'}).text
                    match_dict['home'] = element.find_all("a", {"class":"team-link"})[0].text
                    match_dict['away'] = element.find_all("a", {"class":"team-link"})[1].text
                    match_dict['score'] = element.find("a", {"class":"result-1 rc"}).text
                    match_dict['url'] = link_tag.get("href")
                matches_ls.append(match_dict)
            break
    
    matches_ls = list(filter(None, matches_ls))

    return matches_ls






def translateDate(data):
    
    unwanted = []
    for match in data:
        date = match['date'].split()
        if '?' not in date[0]:
            try:
                match['date'] = ' '.join([TRANSLATE_DICT[date[0]], date[1], date[2]])
            except KeyError:
                print(date)
        else:
            unwanted.append(data.index(match))
    
    # remove matches that got suspended/postponed
    for i in sorted(unwanted, reverse = True):
        del data[i]
    
    return data


def getSortedData(data):

    try:
        data = sorted(data, key = lambda i: dt.strptime(i['date'], '%b %d %Y'))
        return data
    except ValueError:    
        data = translateDate(data)
        data = sorted(data, key = lambda i: dt.strptime(i['date'], '%b %d %Y'))
        return data
    



def getMatchData(driver, url, display=True, close_window=True):
    try:
        driver.get(url)
    except WebDriverException:
        driver.get(url)

    time.sleep(5)
    # get script data from page source
    script_content = driver.find_element(By.XPATH, '//*[@id="layout-wrapper"]/script[1]').get_attribute('innerHTML')


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
    region = driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/span[1]').text
    league = driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/a').text.split(' - ')[0]
    season = driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/a').text.split(' - ')[1]
    if len(driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/a').text.split(' - ')) == 2:
        competition_type = 'League'
        competition_stage = ''
    elif len(driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/a').text.split(' - '))== 3:
        competition_type = 'Knock Out'
        competition_stage = driver.find_element(By.XPATH, '//*[@id="breadcrumb-nav"]/a').text.split(' - ')[-1]
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
    if display:
        print('Region: {}, League: {}, Season: {}, Match Id: {}'.format(region, league, season, match_data['matchId']))
    
    
    if close_window:
        driver.close()
        
    return match_data





def createEventsDF(data):
    events = data['events']
    for event in events:
        event.update({'matchId' : data['matchId'],
                        'startDate' : data['startDate'],
                        'startTime' : data['startTime'],
                        'score' : data['score'],
                        'ftScore' : data['ftScore'],
                        'htScore' : data['htScore'],
                        'etScore' : data['etScore'],
                        'venueName' : data['venueName'],
                        'maxMinute' : data['maxMinute']})
    events_df = pd.DataFrame(events)

    # clean period column
    events_df['period'] = pd.json_normalize(events_df['period'])['displayName']

    # clean type column
    events_df['type'] = pd.json_normalize(events_df['type'])['displayName']

    # clean outcomeType column
    events_df['outcomeType'] = pd.json_normalize(events_df['outcomeType'])['displayName']

    # clean outcomeType column
    try:
        x = events_df['cardType'].fillna({i: {} for i in events_df.index})
        events_df['cardType'] = pd.json_normalize(x)['displayName'].fillna(False)
    except KeyError:
        events_df['cardType'] = False

    eventTypeDict = data['matchCentreEventTypeJson']  
    events_df['satisfiedEventsTypes'] = events_df['satisfiedEventsTypes'].apply(lambda x: [list(eventTypeDict.keys())[list(eventTypeDict.values()).index(event)] for event in x])

    # clean qualifiers column
    try:
        for i in events_df.index:
            row = events_df.loc[i, 'qualifiers'].copy()
            if len(row) != 0:
                for irow in range(len(row)):
                    row[irow]['type'] = row[irow]['type']['displayName']
    except TypeError:
        pass


    # clean isShot column
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        if 'isShot' in events_df.columns:
            events_df['isShot'] = events_df['isShot'].replace(np.nan, False).infer_objects(copy=False)
        else:
            events_df['isShot'] = False

        # clean isGoal column
        if 'isGoal' in events_df.columns:
            events_df['isGoal'] = events_df['isGoal'].replace(np.nan, False).infer_objects(copy=False)
        else:
            events_df['isGoal'] = False

    # add player name column
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        events_df.loc[events_df.playerId.notna(), 'playerId'] = events_df.loc[events_df.playerId.notna(), 'playerId'].astype(int).astype(str)    
    player_name_col = events_df.loc[:, 'playerId'].map(data['playerIdNameDictionary']) 
    events_df.insert(loc=events_df.columns.get_loc("playerId")+1, column='playerName', value=player_name_col)

    # add home/away column
    h_a_col = events_df['teamId'].map({data['home']['teamId']:'h', data['away']['teamId']:'a'})
    events_df.insert(loc=events_df.columns.get_loc("teamId")+1, column='h_a', value=h_a_col)


    # adding shot body part column
    events_df['shotBodyType'] =  np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        for i in events_df.loc[events_df.isShot==True].index:
            for j in events_df.loc[events_df.isShot==True].qualifiers.loc[i]:
                if j['type'] == 'RightFoot' or j['type'] == 'LeftFoot' or j['type'] == 'Head' or j['type'] == 'OtherBodyPart':
                    events_df.loc[i, 'shotBodyType'] = j['type']


    # adding shot situation column
    events_df['situation'] =  np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        for i in events_df.loc[events_df.isShot==True].index:
            for j in events_df.loc[events_df.isShot==True].qualifiers.loc[i]:
                if j['type'] == 'FromCorner' or j['type'] == 'SetPiece' or j['type'] == 'DirectFreekick':
                    events_df.loc[i, 'situation'] = j['type']
                if j['type'] == 'RegularPlay':
                    events_df.loc[i, 'situation'] = 'OpenPlay' 

    event_types = list(data['matchCentreEventTypeJson'].keys())
    event_type_cols = pd.DataFrame({event_type: pd.Series([event_type in row for row in events_df['satisfiedEventsTypes']]) for event_type in event_types})
    events_df = pd.concat([events_df, event_type_cols], axis=1)


    return events_df
    



def createMatchesDF(data):
    columns_req_ls = ['matchId', 'attendance', 'venueName', 'startTime', 'startDate',
                      'score', 'home', 'away', 'referee']
    matches_df = pd.DataFrame(columns=columns_req_ls)
    if type(data) == dict:
        matches_dict = dict([(key,val) for key,val in data.items() if key in columns_req_ls])
        matches_df = pd.DataFrame(matches_dict, columns=columns_req_ls).reset_index(drop=True)
        matches_df[['home', 'away']] = np.nan  
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            matches_df['home'].iloc[0] = [data['home']]
            matches_df['away'].iloc[0] = [data['away']]
    else:
        for match in data:
            matches_dict = dict([(key,val) for key,val in match.items() if key in columns_req_ls])
            matches_df = pd.DataFrame(matches_dict, columns=columns_req_ls).reset_index(drop=True)
    
    matches_df = matches_df.set_index('matchId')        
    return matches_df




def load_EPV_grid(fname='EPV_grid.csv'):
    """ load_EPV_grid(fname='EPV_grid.csv')
    
    # load pregenerated EPV surface from file. 
    
    Parameters
    -----------
        fname: filename & path of EPV grid (default is 'EPV_grid.csv' in the curernt directory)
        
    Returns
    -----------
        EPV: The EPV surface (default is a (32,50) grid)
    
    """
    epv = np.loadtxt(fname, delimiter=',')
    return epv






def get_EPV_at_location(position,EPV,attack_direction,field_dimen=(106.,68.)):
    """ get_EPV_at_location
    
    Returns the EPV value at a given (x,y) location
    
    Parameters
    -----------
        position: Tuple containing the (x,y) pitch position
        EPV: tuple Expected Possession value grid (loaded using load_EPV_grid() )
        attack_direction: Sets the attack direction (1: left->right, -1: right->left)
        field_dimen: tuple containing the length and width of the pitch in meters. Default is (106,68)
            
    Returrns
    -----------
        EPV value at input position
        
    """
    
    x,y = position
    if abs(x)>field_dimen[0]/2. or abs(y)>field_dimen[1]/2.:
        return 0.0 # Position is off the field, EPV is zero
    else:
        if attack_direction==-1:
            EPV = np.fliplr(EPV)
        ny,nx = EPV.shape
        dx = field_dimen[0]/float(nx)
        dy = field_dimen[1]/float(ny)
        ix = (x+field_dimen[0]/2.-0.0001)/dx
        iy = (y+field_dimen[1]/2.-0.0001)/dy
        return EPV[int(iy),int(ix)]



                

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
    return data




def addEpvToDataFrame(data):

    # loading EPV data
    EPV = load_EPV_grid('EPV_grid.csv')

    # converting opta coordinates to metric coordinates
    data = to_metric_coordinates_from_whoscored(data)

    # calculating EPV for events
    EPV_difference = []
    for i in data.index:
        if data.loc[i, 'type'] == 'Pass' and data.loc[i, 'outcomeType'] == 'Successful':
            start_pos = (data.loc[i, 'x_metrica'], data.loc[i, 'y_metrica'])
            start_epv = get_EPV_at_location(start_pos, EPV, attack_direction=1)
            
            end_pos = (data.loc[i, 'endX_metrica'], data.loc[i, 'endY_metrica'])
            end_epv = get_EPV_at_location(end_pos, EPV, attack_direction=1)
            
            diff = end_epv - start_epv
            EPV_difference.append(diff)
            
        else:
            EPV_difference.append(np.nan)
    
    data = data.assign(EPV_difference = EPV_difference)
    
    
    # dump useless columns
    drop_cols = ['x_metrica', 'endX_metrica', 'y_metrica',
                 'endY_metrica']
    data.drop(drop_cols, axis=1, inplace=True)
    data.rename(columns={'EPV_difference': 'EPV'}, inplace=True)
    
    return data














