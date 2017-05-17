# -*- coding: utf-8 -*-
"""
Created on Fri Sep  9 17:00:35 2016

@author: tyler
"""
import os, glob
import gzip
import pdb
import numpy as np
import re
import pandas as pd
#import matplotlib
import logging
from mpl_toolkits.basemap import Basemap, cm
from matplotlib.colors import LinearSegmentedColormap
from scipy.interpolate import griddata
import datetime
#plt.ioff()



class make_snow_db:
    def __init__(self,data_dir,output_dir,zip_dir,db_name,grid_size,hdf5_name):
        logging.debug('initializing object')
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.zip_dir = zip_dir
        self.grid_size = grid_size

        self.hdf5_name = hdf5_name

        
        self.connect_to_db()
        
        
        self.time_series_collection = self.db[self.collection_name]

        #generate indicies
        index_array  = np.mgrid[0:grid_size, 0:grid_size].swapaxes(0,2).swapaxes(0,1)
        self.indicies = index_array.reshape((grid_size)*(grid_size),2)
        
        self.init_hdf5()
    
    def __exit__(self):
        logging.debug('exiting class. closing hdf5 hdf5')
        self.fh5.close()
    def init_hdf5(self):
        logging.debug('initializing hdf5')
        self.fh5 = h5py.File(os.path.join(self.data_dir,self.hdf5_name), "r+")
    
    def init_time_series_data_set(self):
        #create body dataset type: comprised of a timestamp and data
        comp_type = np.dtype([('timestamp', np._str(), ('daily_matrix', 'i8')])
        #create dataset body
        self.body_dset = self.fh5.create_dataset(dset_name,(self.grid_size, self.grid_size,),maxshape=(self.grid_size, self.grid_size,None),dtype='i8', compression="lzf")

        
    def parse_timeseries(self):
"""
assumes hdf5 is setup for the correct resuolution
"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        #os.chdir(zip_dir)
        for path, dirs, files in os.walk(self.zip_dir):
            for folder_name in dirs:
                print('in dir:{0} '.format(folder_name))
                print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                input_dir = os.path.join(self.zip_dir,folder_name)
                self.add_to_hdf5(input_dir)
                #df_year.to_csv(self.output_dir+folder_name+'.csv')
                print('done and file saved, moving on from {0} '.format(folder_name))

                print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print('all done')

    def make_false_coverage_df(self):
"""
to be removed. an entirely different class make_time_series shall use this function.
"""
        data_perc_cov = []
        data_cov = []
        index_ts = []      
        file_names = sorted(glob.glob(self.output_dir+"*.h5"), key = lambda x: x.rsplit('.', 1)[0])
        #only snow and ice are captured (1), else 0
        def snow_and_ice(x):
            if x==4 or x==3:
                x=1 
            else: 
                x=0
            return x        

        total_area = self.df.shape[0]*24*24 #does not use area
        for f in file_names:
            print('inside file {}'.format(f))
            try:
                with pd.io.pytables.HDFStore(f) as year_store:
                    for series_name in year_store.keys():
                        s_snow_ice = np.array(map(lambda x: snow_and_ice(x), year_store[series_name].values))
                        if np.sum(s_snow_ice) == 0:
                            logging.warning('check {0}. it contains no snow and ice:'.format(series_name) ) 
                        snow_ice_area = 24*24*s_snow_ice.sum()
                        timestamp = series_name.strip('/series_')
                        index_ts.append(timestamp)
                        perc_cov = np.divide(snow_ice_area, total_area)
                        data_perc_cov.append(perc_cov)
                        data_cov.append(snow_ice_area)
            except:
                logging.warning('check {0}. it cant be opened:'.format(f) ) 
                pass
           
        index_datetime = pd.to_datetime(index_ts, format='%Y_%m_%d')
        df = pd.DataFrame(columns = ['perc coverage', 'coverage (km^2)'], index = index_datetime)
        df.index.name = 'timestamp'        
        df['perc coverage'] = data_perc_cov
        df['coverage (km^2)'] = data_cov   
        return df        

    def make_coverage_df(self):    
"""
to be removed. an entirely different class make_time_series shall use this function.
"""            
        data_perc_cov = []
        data_cov = []
        index_ts = []      
        file_names = sorted(glob.glob(os.path.join(self.output_dir,"*.h5")), key = lambda x: x.rsplit('.', 1)[0])        
        #only snow and ice are captured (1), else 0
        def snow_and_ice(x):
            if x==4 or x==3:
                x=1 
            else: 
                x=0
            return x        
        
        total_area = self.df['area'].sum()
        for f in file_names:
            print('inside file {}'.format(f))
            try:
                with pd.HDFStore(f) as year_store:
                    for series_name in year_store.keys():
                        data = year_store[series_name]
                        s_snow_ice = np.array(map(lambda x: snow_and_ice(x), data.values))
                        if np.sum(s_snow_ice) == 0:
                            logging.warning('check {0}. it contains no snow and ice:'.format(series_name) ) 
                        snow_ice_area = np.dot(s_snow_ice, self.df['area'].values)
                        timestamp = series_name.strip('/series_')
                        index_ts.append(timestamp)
                        perc_cov = np.divide(snow_ice_area, total_area)
                        data_perc_cov.append(perc_cov)
                        data_cov.append(snow_ice_area)
            except:
                logging.warning('check {0}. it cant be opened:'.format(f) ) 
                pass
           
        index_datetime = pd.to_datetime(index_ts, format='%Y_%m_%d')
        df = pd.DataFrame(columns = ['perc coverage', 'coverage (km^2)'], index = index_datetime)
        df.index.name = 'timestamp'        
        df['perc coverage'] = data_perc_cov
        df['coverage (km^2)'] = data_cov   
        return df
        

    def add_to_hdf5(self,directory):

        logging.debug('enered add_to_hdf5. adding snow and ice data to hdf5:{0} in directory: {1}'.format(self.hdf5_name,directory) )  

        #output_df = pd.DataFrame() replaced with year_store

        if not os.path.exists(directory):
            logging.warning('directory does not exist: {0}'.format(directory))
        
        for path, dirs, files in os.walk(directory):
            logging.debug('path: {0} \n dirs: {1}'.format(path,dirs))
            for filename in [f for f in files if f.endswith(".gz")]:
                logging.debug('reading file: {}'.format(filename))
                
                colName = filename.split('_', 1)[0].replace('ims', '')
                colName = colName[0:4]+'_'+colName[4:]
                dt = datetime.datetime.strptime(colName,'%Y_%j')
                dset_name = dt.strftime('%Y_%m_%d')

                add_body_to_hdf5(path,filename, dset_name)
    

    def add_body_to_hdf5(path,filename, dset_name):
        logging.debug('inside add_body_to_hdf5 for date: {}'.format(dset_name))
        with gzip.open(os.path.join(path, filename), 'r') as f:
            threashold = 75
            for i, line in enumerate(f):

                if re.search('0{30,}', line):
                    logging.info('nominally formatted data starting line: {}'.format(i))
                    nominally_formatted_bool = True
                    start_line = i
                    break
    
                if re.search('0    0    0    0    0    0    0    0', line):
                    logging.info('data found at index: {}'.format(i))
                    logging.debug('unpacked data found for filename: {}'.format(filename))
                    nominally_formatted_bool = False
                    start_line = i
                    break
                if i > threashold:
                    logging.error('cant distinguish header for filename: {}'.format(filename))
                    break 
        
            if nominally_formatted_bool:
                for i, line in enumerate(f[start_line:-1]):
                    line = line.strip('\r') #sometimes there is a newline
                    int_line = map(lambda x: int(x) ,line)
                    try:
                        body_dset[i,:] = int_line
                    except:
                        logging.warning('problem occured when adding to hdf5')
                        logging.warning('not going to add this data: {}'.format(filename))
            
            #this only happens on the small 24,24 dataset. no loop required.
            else:
                int_body = []
                for i, line in enumerate(f):
                    line = line.replace(' ','')
                    line = line.strip('\r')
                    line = line.replace('164','3')
                    line = line.replace('165','4')
                    int_body.append([int(c) for c in line]) 
                try:
                    flat_body = [item for sublist in int_body for item in sublist]
                    body_m = np.matrix([flat_body])
                    #need to flip matrix from left to right.
                    body_m=body_m.reshape(1024,1024) #only occurs in 24km grid
                    body_dset = body_m
                except:
                    logging.warning('problem occured when adding uncompressed formatted file to hdf5')
                    logging.warning('not going to add this data: {}'.format(filename))
                    pass   
        if not 4 in body_dset:
            logging.warning('no snow reported for filename: {}'.format(filename))
            
        logging.debug('added to hdf5 for date: {}'.format(date))        
        fh5.flush()


                        
    def parse_normally_formatted_file(self,body,filename):
        """
        Normally, the files are in a nxn matrix, with no spaces. This function
        will flatten out the body into a list and filter the
        points included in the lat_long_indicies
        """

        int_body = body
        for i, line in enumerate(body):
            try:
                line = line.strip('\r') #sometimes there is a newline
                int_body[i] = [int(c) for c in line]
            except ValueError as err:
                logging.warning('value error: {0}'.format(err))
                logging.warning('not going to add this data: {}'.format(filename))
                pass
        
        body_m = np.matrix(int_body)
        #need to flip matrix from left to right.
        body_m = np.fliplr(body_m)
        data = body_m[self.rows,self.columns].tolist()[0]
        return data
        
    def parse_alternatively_formatted_file(self,body, filename):
        """
        Some files are of a different format. ice is set as 164 and snow as 165.
        Also, the shape is not quite the same nxn matrix. This also contains
        spaces that need to be removed. Lastly, this format contains no land
        and sea indicators (1,2). This function adds it back in via add_land.
        Once these fomatting changes are made, This function will flatten out
        the body into a list and filter the points included in the 
        lat_long_indicies.
        """                            
        int_body = []
        for i, line in enumerate(body):
            line = line.replace(' ','')
            line = line.replace('164','3')
            line = line.replace('165','4')
            int_body.append([int(c) for c in line]) 
        try:
            flat_body = [item for sublist in int_body for item in sublist]
            body_m = np.matrix([flat_body])
            #need to flip matrix from left to right.
            body_m=body_m.reshape(1024,1024) #only occurs in 24km grid
            body_m = np.fliplr(body_m)
            
            reduced_body = body_m[self.rows,self.columns].tolist()[0]
            flat_body_land = self.add_land(reduced_body) 
        except ValueError as err:
                logging.warning('value error: {0}'.format(err))
                logging.warning('not going to add this data: {}'.format(filename))
                pass
        return flat_body_land
        
    #value error if this function is defined in add_land                    
    def build_terrain(self,x,y): 
        logic_matrix = np.matrix([ [1, 1, 1, 1, 1 ], #row: x is reporting space
                                 [0, 1, 0, 1, 0 ], #x is reporting water
                                 [0, 0, 1, 0, 1 ], #x is reporting land
                                 [1, 1, 1, 1, 1 ], #x is reporting ice
                                 [1, 1, 1, 1, 1 ]] )#x is reporting snow                                   
        if y == 1:
            logging.warning( 'thats odd, water is reported on my matrix')
        if y == 2:
            logging.warning( 'thats odd, land is being reported on my matrix')
        if logic_matrix[x,y] == 0:
            return x
        elif logic_matrix[x,y] == 1:
            return y
        else:
            logging.error( 'check logic matrix')
            return y    
                   
    def add_land(self,m):
        try:                                  
            m_with_land_list = map( lambda no_snow_elem,matrix_elem : self.build_terrain(no_snow_elem,matrix_elem), self.df['noSnowMap'].values.tolist(), m)       
            return m_with_land_list 
        except ValueError as err:
            #inputLen = len(m) 
            #noSnowLen = len(self.df['noSnowMap'].values.tolist())
            logging.error('lists have to be the same length: {0}'.format(err))