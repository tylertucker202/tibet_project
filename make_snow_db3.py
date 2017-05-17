# -*- coding: utf-8 -*-
"""
Created on Fri Sep  9 17:00:35 2016

@author: tyler
"""
import os
import gzip
import pdb
import numpy as np
import re
#import matplotlib
import logging
import datetime
import h5py
import scipy.sparse as sparse
#plt.ioff()
from itertools import islice

        

class make_snow_hdf5:
    def __init__(self, data_dir,output_dir,grid_size):
        logging.debug('initializing object')
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.grid_size = grid_size        
        
        hdf5_name = os.path.basename(data_dir)
        self.init_hdf5(hdf5_name)
    
    def __exit__(self):
        logging.debug('exiting class. closing hdf5 hdf5')
        self.fh5.close()
        
    def init_hdf5(self, hdf5_name):
        logging.debug('initializing hdf5')
        
        full_name = os.path.join(self.output_dir, hdf5_name)
        self.fh5 = h5py.File(full_name+'.hdf5', "w")
        
        #create dataset body
        self.fh5.create_dataset('snow_data',
            (self.grid_size, self.grid_size,366),
            dtype='i8', compression="lzf", 
            fillvalue=np.nan)
        
    def create_hdf5_group(self, year):
        logging.debug('initializing group for year: {}'.format(year))
        grp = self.fh5.create_group(year)
        grp.create_dataset("date", (366, ), dtype="S10", fillvalue="")
        grp.create_dataset("corrupted", (366, ), dtype=bool, fillvalue=False)
        grp.create_dataset("zipped_format", (366, ), dtype=bool, fillvalue=True)
        grp.create_dataset("snow_data", (self.grid_size, self.grid_size,366), dtype='i8',compression="gzip", compression_opts=9)
        return grp
        
    def parse_timeseries(self):
        """
        assumes hdf5 is setup for the correct resuolution
        """
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        #os.chdir(zip_dir)
        for path, dirs, files in os.walk(self.data_dir):
            for folder_name in dirs:
                print('in dir:{0} '.format(folder_name))
                print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                group = self.create_hdf5_group(folder_name)

                input_dir = os.path.join(self.data_dir,folder_name)
                self.add_data_sets_to_group(group, input_dir)
                #df_year.to_csv(self.output_dir+folder_name+'.csv')
                print('done and file saved, moving on from {0} '.format(folder_name))

                print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print('all done')
        

    def add_data_sets_to_group(self,group, input_dir):

        logging.debug('entered add_rows_to_hdf5. adding snow and ice data to hdf5: in input_dir: {0}'.format(input_dir) )  


        if not os.path.exists(input_dir):
            logging.warning('directory does not exist: {0}'.format(input_dir))
        
        for path, dirs, files in os.walk(input_dir):
            logging.debug('path: {0} \n dirs: {1}'.format(path,dirs))
            for filename in [f for f in files if f.endswith(".gz")]:
                logging.debug('reading file: {}'.format(filename))
                
                colName = filename.split('_', 1)[0].replace('ims', '')
                colName = colName[0:4]+'_'+colName[4:]
                dt = datetime.datetime.strptime(colName,'%Y_%j')
                dset_name = dt.strftime('%Y-%m-%d')
                
                day_of_year_idx = int(dt.strftime('%j'))-1 #index starts with zero
                group['date'][day_of_year_idx] = dset_name

                self.add_group_datasets_to_hdf5(path,filename, group, day_of_year_idx)
    

    def add_group_datasets_to_hdf5(self,path,filename, group, day_of_year_idx):
        logging.debug('inside add_group_datasets_to_hdf5 for index: {}'.format(day_of_year_idx))
        with gzip.open(os.path.join(path, filename), 'r') as f:
        #with gzip.open(os.path.join(path, filename), 'r') as f:
            threashold = 75
            for i, line in enumerate(f):

                if re.search('0{30,}', line):
                    logging.info('nominally formatted data starting line: {}'.format(i))
                    nominally_formatted_bool = True
                    start_line = i
                    group['zipped_format'][day_of_year_idx] = True
                    group['corrupted'][day_of_year_idx] = False
                    break
    
                if re.search('0    0    0    0    0    0    0    0', line):
                    logging.info('data found at index: {}'.format(i))
                    logging.debug('unpacked data found for filename: {}'.format(filename))
                    nominally_formatted_bool = False
                    start_line = i
                    group['zipped_format'][day_of_year_idx] = False
                    group['corrupted'][day_of_year_idx] = False
                    break
                if i > threashold:
                    logging.error('cant distinguish header for filename: {}'.format(filename))
                    group['corrupted'][day_of_year_idx] = True
                    break 
                
            #continue parsing, starting at start_line
        with gzip.open(os.path.join(path, filename), 'r') as f:    
            if nominally_formatted_bool:
    
                for idx, line in enumerate(islice(f, start_line, None)):
    
                    line = line.strip('\n') #sometimes there is a newline
                    line = line.replace('1','0')
                    line = line.replace('2','0')
                    int_line = map(lambda x: int(x) ,line)          
                    
                    #remove land and sea to save space
                    #snow_line = [0 if x==1 or x==2 else x for x in int_line]
                    snow_line = int_line
                    
                    try:
                        group['snow_data'][idx,:,day_of_year_idx] = snow_line
                    except:
                        logging.warning('problem occured when adding compressed format data to hdf5')
                        logging.warning('not going to add this data: {}'.format(filename))
                        group['corrupted'][day_of_year_idx] = True
                        pass
                    
                    #check if snow exists in middle row
                    if idx == self.grid_size/2:
                        if not (4 in int_line) or (not 3 in int_line):
                            logging.warning('no snow or ice displayed on middle row...setting as corrupt')
                            group['corrupted'][day_of_year_idx] = True

            #this only happens on the small 24,24 dataset. no loop required.
            else:
                int_body = []
                for idx, line in enumerate(islice(f, start_line, None)):
                    
                    line = line.replace(' ','')
                    line = line.strip('\n')
                    line = line.replace('164','3')
                    line = line.replace('165','4')
                    int_body.append([int(c) for c in line])
                try:
                    flat_body = [item for sublist in int_body for item in sublist]
                    body_m = np.matrix([flat_body])
                    body_m = body_m.reshape(1024,1024) #only occurs in 24km grid
                    group['snow_data'][:,:,day_of_year_idx]= body_m
                except:
                    pdb.set_trace()
                    logging.warning('problem occured when adding uncompressed format data to hdf5')
                    logging.warning('not going to add this data: {}'.format(filename))
                    pass   
                if not 4 in body_m:
                    logging.warning('no snow reported for filename: {}'.format(filename))
                    group['corrupted'][day_of_year_idx] = True
            
        logging.debug('added to hdf5 for index: {}'.format(day_of_year_idx))        
        self.fh5.flush()
        
if __name__ == '__main__':
    
    home_dir = os.getcwd()
    input_data_dir = os.path.join(home_dir,'zip_files', '24km_test')
    output_dir = os.path.join(os.getcwd(), os.pardir, 'output')
    grid_size = 1024
    
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=FORMAT,filename=os.path.join(output_dir,'make_snow_hdf5.log'),level=logging.DEBUG)
    logging.debug('Start of log file')   
    

    logging.debug('init object')
    snw_hdf5 = make_snow_hdf5(input_data_dir,output_dir,grid_size)
    logging.debug('Parse series')
    snw_hdf5.parse_timeseries()
    
    ###to be used for testing
    fh5 = h5py.File('24km_test.hdf5', "r")
    
    #check if all keys have been added
    fh5.keys()
    
    #check if 2013-242 is corrupted
    fh5['2013'].keys()
    fh5['2013']['corrupted'][0] #should be false
    fh5['2013']['corrupted'][242-1] # should be true
    
    #check if 1997 is in zipped format
    fh5['1997']['zipped_format'][127-1] #should be false
    fh5['1997']['zipped_format'][35-1] #should be true
    fh5['1997']['zipped_format'][36-1] #should be true
    
    #check if dates were placed in the right order
    
    
