#!/usr/lib/python2.7/

import sys
import os
import gwy
from math import sqrt
import shutil

directory = '/home/bj002/Documents/PhD_Docs/AFM_processing/disagg_worked/180508-sample2/'

file_list = os.listdir(directory)

def configureGwySettings(s):
	#This function does all the editing of the gwyddion settings file
	#Taken out of the main text in an effort to make code more readable

	#plane-subtract the data
	s["/module/polylevel/col_degree"] = 3
	s["/module/polylevel/do_extract"] = False
	s["/module/polylevel/independent"] = True
	s["/module/polylevel/masking"] = 2 #don't use any mask that might be left over
	s["/module/polylevel/max_degree"] = 3
	s["/module/polylevel/row_degree"] = 3
	s["/module/polylevel/same_degree"] = True

	#'align_rows' function
	s["/module/linematch/direction"] = 0
	s["/module/linematch/do_extract"] = False
	s["/module/linematch/do_plot"] = False
	s["/module/linematch/masking"] = 0
	s["/module/linematch/max_degree"] = 1
	s["/module/linematch/method"] = 1 #uses median
	s["/module/linematch/trim_fraction"] = float(0.05)
		
	#Gaussian filter to remove noise
	s["/module/filter/dialog/position/height"] = 393
	s["/module/filter/dialog/position/width"] = 281
	s["/module/filter/filter_type"] = 7
	s["/module/filter/gauss_size"] = float(1)
	s["/module/filter/masking"] = 2
	s["/module/filter/size"] = 5
	
	#Shamelessly taken from Gwyddion forums - puts a height scale bar on images
	s['/module/pixmap/title_type'] = 0
	#s['/module/pixmap/ztype'] = 0
	s['/module/pixmap/xytype'] = 2
	s['/module/pixmap/draw_maskkey'] = False
	s['/module/pixmap/transparent_bg'] =  True
	
	#Export image with the mask on
	s['/module/pixmap/draw_mask'] = False
	
	#Font and linewidth info
	s['/module/pixmap/font'] =  "Liberation Serif Bold"
	s['/module/pixmap/line_width'] =  float(2)
	s["/module/pixmap/scale_font"] = True
	s['/module/pixmap/font_size'] =  float(12)
		
	#Put a scale bar for 500 nm on the image
	s['/module/pixmap/inset_draw_label'] = True
	s['/module/pixmap/inset_draw_text_above'] = True
	s['/module/pixmap/inset_draw_ticks'] = False
	s['/module/pixmap/inset_length'] = "200 nm"
	s["/module/pixmap/inset_pos"] = 3 #bottom left = 3
		
	#Keep the original image parameters - e.g. number of pixels
	s["/module/pixmap/xytype"] = 2
	s["/module/pixmap/zoom"] = float(1)
	s["/module/pixmap/ztype"] = 1
		
def makeBinaryMask(container, channel_ID):
	
	datafield = container['/%d/data' % channel_ID]
             
	# Calculate min, max and range of data to allow calculation of relative value for grain thresholding
	#I think this is too 'brutal' a way of finding relative threshold
	#Something like top/bottom 10% might be better
	#Don't think that the otsu uses the full data range in this way
	min_datarange = datafield.get_min()
	max_datarange = datafield.get_max()
	#print datafield.get_rms()
	data_range = abs(max_datarange - min_datarange)

	# Calculate Otsu threshold for data           
	o_threshold = datafield.otsu_threshold()

	# Calculate relative threshold for grain determination
	rel_threshold = (100 * (o_threshold/data_range))*sqrt(2) #Not sure this is scaling properly
 
 
	# Mask grains
	mask = gwy.DataField.duplicate(datafield)
	datafield.grains_mark_height(mask, 30, False)
	
	#Using grains to make a binary mask
	binary_mask = mask
	gwy_rawdata['/%d/mask' % channel_ID] = binary_mask

for file_name in file_list:
	if file_name[-4:] == '.spm':
		full_file_name = directory + file_name
		
		try:
			spm_file_list.append(full_file_name)
		except NameError:
			spm_file_list = [full_file_name]

for image in spm_file_list:
	
	#Load the image and make it current in the gwyddion data browser
	gwy_rawdata = gwy.gwy_file_load(image, gwy.RUN_NONINTERACTIVE)
	gwy.gwy_app_data_browser_add(gwy_rawdata)	
	
	#Find the id locators for the height
	height_ids = gwy.gwy_app_data_browser_find_data_by_title(gwy_rawdata, 'Height')

	#Get the settings for each function from the saved settings file (~/.gwyddion/settings)
	s = gwy.gwy_app_settings_get()
	configureGwySettings(s)

	#Process both trace and retrace
	for i in height_ids:
		
		###
		### CORRECTING THE DATA WITH GWYDDION FUNCTIONS
		### HAVE INCREDIBLY UNPLEASANT LOOKING EDITING OF SETTINGS TO DO FOR EACH FUNCTION
		### PROBABLY A NEATER WAY TO DO THIS BUT CBA TO LOOK FOR IT NOW
		### COPIED THE SETTINGS FROM THE ~/.gwyddion/settings file
		### 
		
		gwy.gwy_app_data_browser_select_data_field(gwy_rawdata, i)
		
		#level the data
		gwy.gwy_process_func_run('level', gwy_rawdata, gwy.RUN_IMMEDIATE)
		
		#flatten the data
		gwy.gwy_process_func_run('flatten_base', gwy_rawdata, gwy.RUN_IMMEDIATE)
		
		#remove scars
		gwy.gwy_process_func_run('scars_remove', gwy_rawdata, gwy.RUN_IMMEDIATE)
		
		#execute 'align_rows' function
		#s["/module/linematch/method"] = 2
		#gwy.gwy_process_func_run('align_rows', gwy_rawdata, gwy.RUN_IMMEDIATE)
		
		#Gaussian filter to remove noise
		current_data = gwy.gwy_app_data_browser_get_current(gwy.APP_DATA_FIELD)
		current_data.filter_gaussian(0.75)
		current_data.data_changed() #not sure this line is needed
		
		makeBinaryMask(gwy_rawdata, i)
		
		#polynomial correction with masked height
		s["/module/polylevel/masking"] = 0
		gwy.gwy_process_func_run('polylevel', gwy_rawdata, gwy.RUN_IMMEDIATE)
		
		#remove scars
		#gwy.gwy_process_func_run('scars_remove', gwy_rawdata, gwy.RUN_IMMEDIATE)
			
		#Re-do align rows with masked heights
		s["/module/linematch/masking"] = 0
		s["/module/linematch/method"] = 0
		gwy.gwy_process_func_run('align_rows', gwy_rawdata, gwy.RUN_IMMEDIATE)
		
		#makeBinaryMask(gwy_rawdata, i)
		#Re-do align rows with masked heights
		s["/module/linematch/masking"] = 0
		s["/module/linematch/method"] = 0
		#gwy.gwy_process_func_run('align_rows', gwy_rawdata, gwy.RUN_IMMEDIATE)
		
		#Set zero to mean value
		gwy.gwy_process_func_run('zero_mean', gwy_rawdata, gwy.RUN_IMMEDIATE)
		
		###
		### SAVING THE MODIFIED FILES AS TIFFS
		###
		
		#Save all files as tiffs - this puts them all with the raw data annoyingly
		#Could put in some os commands to move everything around afterwards
	
		#Use blue and gold colour scheme with a sensible and consistent colour scale
		maximum_disp_value = gwy_rawdata.set_int32_by_name("/"+str(i)+"/base/range-type", int(1))
		minimum_disp_value = gwy_rawdata.set_double_by_name("/"+str(i)+"/base/min", float(1e-9))
		maximum_disp_value = gwy_rawdata.set_double_by_name("/"+str(i)+"/base/max", float(20e-9))
		palette = gwy_rawdata.set_string_by_name("/"+str(i)+"/base/palette", "BlueandGold")
		
		if i == 4: #save trace and retrace seperately - presumably can do this more elegantly
			saved_filename = str(image[:-4]+'_trace.tiff')
			
			gwy.gwy_file_save(gwy_rawdata, saved_filename, gwy.RUN_NONINTERACTIVE)

		else:
			saved_filename = str(image[:-4]+'_retrace.tiff')
		
			gwy.gwy_file_save(gwy_rawdata, saved_filename, gwy.RUN_NONINTERACTIVE)
		
	gwy.gwy_app_data_browser_remove(gwy_rawdata) #close the file once we've finished with it 

