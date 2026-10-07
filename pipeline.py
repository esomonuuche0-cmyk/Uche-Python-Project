#!/usr/bin/env python
# coding: utf-8

# ## Uche's Python Project

# In[6]:


# import our library
import pandas as pd
from pathlib import Path
from datetime import datetime


# In[7]:


# Project paths
BASE_DIR = Path.cwd()
RAW_FOLDER = BASE_DIR/"data"/"raw"
CLEAN_FOLDER = BASE_DIR/"data"/"cleaned"
COMBINE_FOLDER = BASE_DIR/"data"/"combined"
LOG_FOLDER = BASE_DIR/"data"/"logs"

# create folder if they don't exists
RAW_FOLDER.mkdir(parents=True, exist_ok=True)
CLEAN_FOLDER.mkdir(parents=True, exist_ok=True)
COMBINE_FOLDER.mkdir(parents=True, exist_ok=True)
LOG_FOLDER.mkdir(parents=True, exist_ok=True)

MASTER_FILE = COMBINE_FOLDER/"master_data.csv"
PROCESSED_FILE = BASE_DIR/"processed_files.txt"


# In[8]:


today = datetime.today()
today = today.strftime('%Y-%m-%d')

LOG_FILE = LOG_FOLDER/f'pipeline_{today}.log'

def log(message):
    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    msg = f'[{time}] {message}'
    print(msg)

    with open(LOG_FILE, 'a', encoding='utf-8') as file:
        file.write(msg + '\n')


# In[9]:


# load processed files
if PROCESSED_FILE.exists():
    with open(PROCESSED_FILE, 'r', encoding='utf-8') as file:
        processed_files = set(file.read().splitlines())
else: 
    processed_files = set()
processed_files


# In[10]:


# Read files
all_files = list(RAW_FOLDER.glob('*.csv'))

new_files = [file for file in all_files if file.name not in processed_files]

if not (new_files):
    log('No new files found')
    exit()

log(f'found {len(new_files)} new file(s)')
new_files


# In[3]:


# cleaning our data 
cleaned_data = []
for file in new_files:
    try:
        # create table
        data = pd.read_csv(file)

        # standardize column name
        data.columns = data.columns.str.lower().str.strip().str.replace(" ", "_")

        # Handling missing values
        before = len(data)
        data = data.dropna()
        after = len(data)
        log(f"{file.name}: " + f" removed {before - after} rows")

        # change the text in warehouse_region to titlecase, sku_code to uppercase , product_name and category title
        data.loc[:,'warehouse_region'] =  data['warehouse_region'].str.title()
        data.loc[:,'sku_code'] =  data['sku_code'].str.upper()
        data.loc[:,'product_name'] =  data['product_name'].str.title()
        data.loc[:,'category'] =  data['category'].str.title()

        # fix the issue with sku_code
        def fix_sku(d):
            s1 = d[0:3]
            s2 = d[-3:]
            answer = s1 + '-' + s2
            return answer

        data.loc[:,'sku_code'] = data['sku_code'].apply(func= fix_sku)

        # fix the date
        # data.loc[:,'date'] = pd.to_datetime(arg = data['date'], errors = 'raise', dayfirst= True, format='mixed')
        data.loc[:,'date_fixed'] = pd.to_datetime(arg = data['date'], errors = 'coerce', dayfirst= True, format='mixed')
        data.drop(columns =['date'], inplace=True)
        data.rename(columns = {'date_fixed' : 'date'} , inplace = True)


        cleaned_data.append(data)
    except Exception as e:
        log(f'ERROR processing {file.name}: {e}')


# In[4]:


# combine all data 
new_data = pd.concat(cleaned_data, ignore_index=True)
new_data


# In[5]:


# Save clean data


daily_file =  CLEAN_FOLDER/f'cleaned_data_{today}.csv'

new_data.to_csv(daily_file, index=False)

log(f'Cleaned data has been Saved')


# In[ ]:


# create and save master file

if MASTER_FILE.exists():
    master_data = pd.read_csv(MASTER_FILE)
    log(f'Existing master records: {len(master_data)}')
else: 
    master_data = pd.DataFrame()
    log('Master dataset does not exists. Creating it')

# combine master data to the newly cleaned data
if not master_data.empty:
    master_data = pd.concat([master_data, new_data], ignore_index=True)

else:
    master_data = new_data

# remove duplicate from master data
before = len(master_data)
master_data = master_data.drop_duplicates()
after = len(master_data)
log(f'we removed {before - after} duplicate rows')

# save master data to combined folder
master_data.to_csv(MASTER_FILE , index=False)
log(f'Master dataset saved')


# In[ ]:


# mark files as processed
with open(PROCESSED_FILE, 'a', encoding='utf-8') as file:
    for processed in new_files:
        file.write(processed.name + '\n')
log(f'Clean pipe completed successfully')
log(f'Total master records:  {len(master_data)}')

