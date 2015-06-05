'''
Created on Mar 26, 2015

@author: Liyan Xu
'''

from data_access import DataAccess
from society import Society
import statistics

from PyQt4 import QtCore, QtGui
from PyQt4.Qt import QMessageBox, QColorDialog
from PyQt4.QtCore import Qt

# from matplotlib.backends.backend_agg import FigureCanvas
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import numpy

'''
Globals, Constants, and other declarations.
'''


# dbname = 'C:/WolongRun/test_db/SimplifiedDB.mdb'
dbname = 'C:/WolongRun/WolongDB'
dbdriver = '{Microsoft Access Driver (*.mdb)}'
 
model_table_name = 'ModelTable'
household_table_name = 'HouseholdTable'
person_table_name = 'PersonTable'
land_table_name = 'LanduseTable'
business_sector_table_name = 'BusinessSectorTable'
policy_table_name = 'PolicyTable'
stat_table_name = 'StatTable'
version_table_name = 'VersionTable'
 
# Rounds of iteration (years)
simulation_depth = 5
 
# Starting and ending year of simulation
start_year = 2015
end_year = 2030

 
# Get the working database
db = DataAccess(dbname, dbdriver)
 
# Get the table pointers
model_table = DataAccess.get_table(db, model_table_name)
household_table = DataAccess.get_table(db, household_table_name)
person_table = DataAccess.get_table(db, person_table_name)
land_table = DataAccess.get_table(db, land_table_name)
business_sector_table = DataAccess.get_table(db, business_sector_table_name)
policy_table = DataAccess.get_table(db, policy_table_name)
stat_table = DataAccess.get_table(db, stat_table_name)
version_table = DataAccess.get_table(db, version_table_name)



'''
user created main submodules 
'''



def create_scenario(db, scenario_name, model_table_name, model_table, hh_table_name, hh_table, 
                    pp_table_name, pp_table, land_table_name, land_table, 
                    business_sector_table_name, business_sector_table, policy_table_name, policy_table, 
                    stat_table_name, stat_table, simulation_depth, start_year, end_year, gui):

    # Set up an initial value (1%) when clicked so that the user knows it's running.
    refresh_progress_bar(simulation_depth, gui)
    
    # Initialize the society class: create society, household, person, etc instances
    soc = Society(db, model_table_name, model_table, hh_table_name, hh_table, pp_table_name, pp_table, 
                  land_table_name, land_table, business_sector_table_name, business_sector_table, 
                  policy_table_name, policy_table, stat_table_name, simulation_depth, stat_table, 
                  start_year, end_year)
    
    #Start simulation
    for iteration_count in range(simulation_depth):
        step_go(db, soc, start_year, end_year, iteration_count, scenario_name)

        # Set value for the progress bar
        refresh_progress_bar((iteration_count + 1) * 100, gui)
        
    
    # When the simulation is successfully completed, insert a record in the VersionTable
    refresh_version_table(db, scenario_name, start_year, simulation_depth)

    # Then refresh the result review control panel's scenario and variable combo boxes
    refresh_review_panel(gui)
    refresh_analysis_panel(gui)






def step_go(database, society_instance, start_year, end_year, iteration_count, scenario_name):
    
    # If it's the first round of iteration, just get the stats and save the records to database
    # Else, proceed with the simulation in society.step_go, and then get the stats and save the records to database
    if iteration_count == 0:  
        # Do statistics and add records to statistics table in database
        add_stat_results(society_instance, scenario_name)
        
        # Then save updated tables in database
        save_results_to_db(database, society_instance, scenario_name)
        
    # Do the simulation
    Society.step_go(society_instance, start_year, end_year, iteration_count)

    add_stat_results(society_instance, scenario_name)
    
    save_results_to_db(database, society_instance, scenario_name)




def add_stat_results(society_instance, scenario_name):
    
    society_instance.stat_dict = dict()

    # Total population
    pp = statistics.StatClass()
    statistics.StatClass.get_population_count(pp, society_instance, scenario_name)
    
    # Household count
    hh = statistics.StatClass()
    statistics.StatClass.get_household_count(hh, society_instance, scenario_name)
    
    # Dissolved household count
    dhh = statistics.StatClass()
    statistics.StatClass.get_dissolved_household_count(dhh, society_instance, scenario_name)
        
    # Total cash savings
    tc = statistics.StatClass()
    statistics.StatClass.get_total_cash_savings(tc, society_instance, scenario_name)
    
    # Total debt
    tb = statistics.StatClass()
    statistics.StatClass.get_total_debt(tb, society_instance, scenario_name)    
    
    # Total agriculture income
    agi = statistics.StatClass()
    statistics.StatClass.get_total_agriculture_income(agi, society_instance, scenario_name)
    
    # Total temporary job income
    tji = statistics.StatClass()
    statistics.StatClass.get_total_tempjob_income(tji, society_instance, scenario_name)
    
    # Total freight transportation income
    fti = statistics.StatClass()
    statistics.StatClass.get_total_freighttrans_income(fti, society_instance, scenario_name)
    
    # Total passenger transportation income
    pti = statistics.StatClass()
    statistics.StatClass.get_total_passengertrans_income(pti, society_instance, scenario_name)
    
    # Total lodging income
    lgi = statistics.StatClass()
    statistics.StatClass.get_total_lodging_income(lgi, society_instance, scenario_name)
        
    # Total renting income
    rti = statistics.StatClass()
    statistics.StatClass.get_total_renting_income(rti, society_instance, scenario_name)
    
    # Sectors income structure
    sis = statistics.StatClass()
    statistics.StatClass.get_sectors_income_structure(sis, society_instance, scenario_name)

    
    
    
def save_results_to_db(database, society_instance, scenario_name):
    
    # Determine household, people,and land table names
    # Format: Scenario_name + household/people/land
    new_hh_table_name = scenario_name + '_household'
    new_pp_table_name = scenario_name + '_persons'
    new_land_table_name = scenario_name + '_land'
    
    stat_table_name = 'StatTable'
    
        
    # Saving the Household table in the database
      
    # If the table with that name does not exist in the database
    # i.e. in the first round of iteration,
    # Then first create a new table, then insert the records.
    # Otherwise, just find the right table, and then insert the records.
    if DataAccess.get_table(database, new_hh_table_name) == None: 
     
        # Create a new Household table from the variable list of Household Class
        new_household_table_formatter = '('
        for var in society_instance.hh_var_list:
            # Add household variables to the formatter
            new_household_table_formatter += var[0] + ' ' + var[2] + ','  
        new_household_table_formatter = new_household_table_formatter[0: len(new_household_table_formatter) - 1] + ')'
     
        create_table_order = "create table " + new_hh_table_name +''+ new_household_table_formatter
        DataAccess.create_table(database, create_table_order)
        DataAccess.db_commit(database)
 
        # Then insert all households into the new table
        # InsertContent = ''
        for HID in society_instance.hh_dict:
            # Make the insert values for this household
            new_household_record_content = '('
            for var in society_instance.hh_var_list:
                # If the value is string, add quotes
                if var[2] == 'VARCHAR' and getattr(society_instance.hh_dict[HID], var[0]) != None: 
                    new_household_record_content += '\''+ unicode(getattr(society_instance.hh_dict[HID], var[0]))+ '\','
                else:
                    new_household_record_content += unicode(getattr(society_instance.hh_dict[HID], var[0]))+ ','
            # Change the ending comma to a closing parenthesis
            new_household_record_content = new_household_record_content[0:len(new_household_record_content)-1] + ')'
            # Insert one household record
            insert_table_order = "insert into " + new_hh_table_name + ' values ' + new_household_record_content.replace('None','Null') +';'
            DataAccess.insert_table(database, insert_table_order)
        DataAccess.db_commit(database)  
 
     
    else:
        # Just insert all households into the new table
        # InsertContent = ''
        for HID in society_instance.hh_dict:
            # Make the insert values for this household
            new_household_record_content = '('
            for var in society_instance.hh_var_list:
                # If the value is string, add quotes
                if var[2] == 'VARCHAR' and getattr(society_instance.hh_dict[HID], var[0]) != None: 
                    new_household_record_content += '\''+ unicode(getattr(society_instance.hh_dict[HID], var[0]))+ '\','
                else:
                    new_household_record_content += unicode(getattr(society_instance.hh_dict[HID], var[0]))+ ','
            # Change the ending comma to a closing parenthesis
            new_household_record_content = new_household_record_content[0:len(new_household_record_content)-1] + ')'
            # Insert one household record
            insert_table_order = "insert into " + new_hh_table_name + ' values ' + new_household_record_content.replace('None','Null') +';'
            DataAccess.insert_table(database, insert_table_order)
        DataAccess.db_commit(database)        



    # Saving the Person table in the database
      
    # If the table with that name does not exist in the database
    # i.e. in the first round of iteration,
    # Then first create a new table, then insert the records.
    # Otherwise, just find the right table, and then insert the records.
    if DataAccess.get_table(database, new_pp_table_name) == None: # This is most indecent... see dataaccess for details
     
        # Create a new Person table from the variable list of Person Class
        new_person_table_formatter = '('
        for var in society_instance.pp_var_list:
            # Add person variables to the formatter
            new_person_table_formatter += var[0] + ' ' + var[2] + ','  
        new_person_table_formatter = new_person_table_formatter[0: len(new_person_table_formatter) - 1] + ')'
     
        create_table_order = "create table " + new_pp_table_name +''+ new_person_table_formatter
        DataAccess.create_table(database, create_table_order)
        DataAccess.db_commit(database)


        # Then insert all persons into the new table
        # InsertContent = ''
        for HID in society_instance.hh_dict:
            for PID in society_instance.hh_dict[HID].own_pp_dict:
                # Make the insert values for this person
                new_person_record_content = '('
                for var in society_instance.pp_var_list:
                    # If the value is string, add quotes
                    if var[2] == 'VARCHAR' and getattr(society_instance.hh_dict[HID].own_pp_dict[PID], var[0]) != None: 
                        new_person_record_content += '\''+ unicode(getattr(society_instance.hh_dict[HID].own_pp_dict[PID], var[0]))+ '\','
                    else:
                        new_person_record_content += unicode(getattr(society_instance.hh_dict[HID].own_pp_dict[PID], var[0]))+ ','
                # Change the ending comma to a closing parenthesis
                new_person_record_content = new_person_record_content[0:len(new_person_record_content)-1] + ')'
                # Insert one person record
                insert_table_order = "insert into " + new_pp_table_name + ' values ' + new_person_record_content.replace('None','Null') +';'
                DataAccess.insert_table(database, insert_table_order)
            DataAccess.db_commit(database)  
 
     
    else:
        # Just insert all persons into the new table
        # InsertContent = ''
        for HID in society_instance.hh_dict:
            for PID in society_instance.hh_dict[HID].own_pp_dict:
                # Make the insert values for this person
                new_person_record_content = '('
                for var in society_instance.pp_var_list:
                    # If the value is string, add quotes
                    if var[2] == 'VARCHAR' and getattr(society_instance.hh_dict[HID].own_pp_dict[PID], var[0]) != None: 
                        new_person_record_content += '\''+ unicode(getattr(society_instance.hh_dict[HID].own_pp_dict[PID], var[0]))+ '\','
                    else:
                        new_person_record_content += unicode(getattr(society_instance.hh_dict[HID].own_pp_dict[PID], var[0]))+ ','
                # Change the ending comma to a closing parenthesis
                new_person_record_content = new_person_record_content[0:len(new_person_record_content)-1] + ')'
                # Insert one person record
                insert_table_order = "insert into " + new_pp_table_name + ' values ' + new_person_record_content.replace('None','Null') +';'
                DataAccess.insert_table(database, insert_table_order)
            DataAccess.db_commit(database)  





    # Saving the Land table in the database
      
    # If the table with that name does not exist in the database
    # i.e. in the first round of iteration,
    # Then first create a new table, then insert the records.
    # Otherwise, just find the right table, and then insert the records.
    if DataAccess.get_table(database, new_land_table_name) == None: # This is most indecent... see dataaccess for details
     
        # Create a new Land table from the variable list of Land Class
        new_land_table_formatter = '('
        for var in society_instance.land_var_list:
            # Add person variables to the formatter
            new_land_table_formatter += var[0] + ' ' + var[2] + ','  
        new_land_table_formatter = new_land_table_formatter[0: len(new_land_table_formatter) - 1] + ')'
     
        create_table_order = "create table " + new_land_table_name +''+ new_land_table_formatter
        DataAccess.create_table(database, create_table_order)
        DataAccess.db_commit(database)


        # Then insert all land parcels into the new table
        # InsertContent = ''
        for land_parcel in society_instance.land_list:
            # Make the insert values for this land parcel
            new_land_record_content = '('
            for var in society_instance.land_var_list:
                # If the value is string, add quotes
                if var[2] == 'VARCHAR' and getattr(land_parcel, var[0]) != None: 
                    new_land_record_content += '\''+ unicode(getattr(land_parcel, var[0]))+ '\','
                else:
                    new_land_record_content += unicode(getattr(land_parcel, var[0]))+ ','
            # Change the ending comma to a closing parenthesis
            new_land_record_content = new_land_record_content[0:len(new_land_record_content)-1] + ')'
            # Insert one land parcel record
            insert_table_order = "insert into " + new_land_table_name + ' values ' + new_land_record_content.replace('None','Null') +';'
            DataAccess.insert_table(database, insert_table_order)
        DataAccess.db_commit(database)  
 
     
    else:
        # Just insert all land parcels into the new table
        # InsertContent = ''
        for land_parcel in society_instance.land_list:
            # Make the insert values for this household
            new_land_record_content = '('
            for var in society_instance.land_var_list:
                # If the value is string, add quotes
                if var[2] == 'VARCHAR' and getattr(land_parcel, var[0]) != None: 
                    new_land_record_content += '\''+ unicode(getattr(land_parcel, var[0]))+ '\','
                else:
                    new_land_record_content += unicode(getattr(land_parcel, var[0]))+ ','
            # Change the ending comma to a closing parenthesis
            new_land_record_content = new_land_record_content[0:len(new_land_record_content)-1] + ')'
            # Insert one land parcel record
            insert_table_order = "insert into " + new_land_table_name + ' values ' + new_land_record_content.replace('None','Null') +';'
            DataAccess.insert_table(database, insert_table_order)
        DataAccess.db_commit(database)        





    # Saving the Statistics table in the database  
      
    # The data table "StatTable" should be pre-created in the database
    # So no need to consider the case when a such table does not exist.
    for StatID in society_instance.stat_dict:
        # Make the insert values for this household
        stat_record_content = '('
        for var in society_instance.stat_var_list:
            # If the value is string, add quotes
            if var[2] == 'VARCHAR' and getattr(society_instance.stat_dict[StatID], var[0]) != None: 
                stat_record_content += '\''+ unicode(getattr(society_instance.stat_dict[StatID], var[0]))+ '\','
            else:
                stat_record_content += unicode(getattr(society_instance.stat_dict[StatID], var[0]))+ ','
        # Change the ending comma to a closing parenthesis
        stat_record_content = stat_record_content[0:len(stat_record_content)-1] + ')'
        # Insert one household record
        insert_table_order = "insert into " + stat_table_name + ' values ' + stat_record_content.replace('None','Null') +';'
        DataAccess.insert_table(database, insert_table_order)
    DataAccess.db_commit(database)           





def refresh_progress_bar(progress, gui):
    gui.prb_progressBar.setValue(progress)



def refresh_version_table(database, scenario_name, start_year, simulation_depth):
    order = "insert into VersionTable values ('" + scenario_name +"', '', " + str(start_year) + ', ' + str(start_year + simulation_depth) +");"
    DataAccess.insert_table(database, order)
    DataAccess.db_commit(database)
    
    

def refresh_review_panel(gui):
    
    # Refresh the version_table and stat_table cursors
    version_table = DataAccess.get_table(db, version_table_name)
    stat_table = DataAccess.get_table(db, stat_table_name)     
        
    # Get scenario and variable lists for the combo boxes in GUI to display
    scenario_list = list()
    for version in version_table:
        scenario_list.append(str(version[0]))
    
    variable_list = list()

    for record in stat_table:
        if record[3] not in variable_list and record[5] == 0:
            # Exclude the composite indicators
            variable_list.append(record[3])
    

    # Clear current combo boxes
    gui.cmb_select_scenario.clear()
    gui.cmb_select_variable.clear()
                
    # add the items to the respective combo boxes
    if len(scenario_list) != 0:
        gui.cmb_select_scenario.addItems(scenario_list)
    if len(variable_list) != 0:
        gui.cmb_select_variable.addItems(variable_list)    



def refresh_analysis_panel(gui):
    
    '''
    Just deal with the time-series data analysis for now'''
    
    # Refresh the version_table and stat_table cursors
    version_table = DataAccess.get_table(db, version_table_name)
    stat_table = DataAccess.get_table(db, stat_table_name)     
        
    # Get scenario and variable lists for the combo boxes in GUI to display
    scenario_list = list()
    for version in version_table:
        scenario_list.append(str(version[0]))
    
    variable_list = list()

    for record in stat_table:
        if record[3] not in variable_list and record[5] == 1:
            # Include only the composite indicators
            variable_list.append(record[3])
    

    # Clear current combo boxes
    gui.cmb_select_scenario_3.clear()
    gui.cmb_select_variable_3.clear()
                
    # add the items to the respective combo boxes
    if len(scenario_list) != 0:
        gui.cmb_select_scenario_3.addItems(scenario_list)
    if len(variable_list) != 0:
        gui.cmb_select_variable_3.addItems(variable_list)




'''
GUI design and Events handling

'''


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s
 
try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)



class Ui_frm_SEEMS_main(object):
      
  
    def setupUi(self, frm_SEEMS_main):
           
        '''
        The followings are PyQt auto-generated codes from the Qt Designer.
        '''
           
        frm_SEEMS_main.setObjectName(_fromUtf8("frm_SEEMS_main"))
        frm_SEEMS_main.resize(1070, 734)
         
        self.centralwidget = QtGui.QWidget(frm_SEEMS_main)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
         
        self.tab_controlpanel = QtGui.QTabWidget(self.centralwidget)
        self.tab_controlpanel.setGeometry(QtCore.QRect(10, 10, 351, 661))
        self.tab_controlpanel.setObjectName(_fromUtf8("tab_controlpanel"))
         
        self.scenarios_setup = QtGui.QWidget()
        self.scenarios_setup.setObjectName(_fromUtf8("scenarios_setup"))
        self.prb_progressBar = QtGui.QProgressBar(self.scenarios_setup)
        self.prb_progressBar.setGeometry(QtCore.QRect(10, 590, 321, 23))
        self.prb_progressBar.setProperty("value", 0)
        self.prb_progressBar.setObjectName(_fromUtf8("prb_progressBar"))
        self.btn_start_simulation = QtGui.QPushButton(self.scenarios_setup)
        self.btn_start_simulation.setGeometry(QtCore.QRect(90, 540, 151, 34))
        self.btn_start_simulation.setObjectName(_fromUtf8("btn_start_simulation"))
        self.lbl_input_scenario_name_label = QtGui.QLabel(self.scenarios_setup)
        self.lbl_input_scenario_name_label.setGeometry(QtCore.QRect(10, 490, 121, 19))
        self.lbl_input_scenario_name_label.setObjectName(_fromUtf8("lbl_input_scenario_name_label"))
        self.txt_input_scenario_name = QtGui.QLineEdit(self.scenarios_setup)
        self.txt_input_scenario_name.setGeometry(QtCore.QRect(140, 490, 191, 25))
        self.txt_input_scenario_name.setObjectName(_fromUtf8("txt_input_scenario_name"))
        self.tab_controlpanel.addTab(self.scenarios_setup, _fromUtf8(""))
        self.results_review = QtGui.QWidget()
        self.results_review.setObjectName(_fromUtf8("results_review"))
        self.cmb_select_scenario = QtGui.QComboBox(self.results_review)
        self.cmb_select_scenario.setGeometry(QtCore.QRect(130, 20, 201, 25))
        self.cmb_select_scenario.setObjectName(_fromUtf8("cmb_select_scenario"))
        self.lbl_select_scenario_label = QtGui.QLabel(self.results_review)
        self.lbl_select_scenario_label.setGeometry(QtCore.QRect(10, 20, 121, 19))
        self.lbl_select_scenario_label.setObjectName(_fromUtf8("lbl_select_scenario_label"))
        self.btn_plot = QtGui.QPushButton(self.results_review)
        self.btn_plot.setGeometry(QtCore.QRect(110, 550, 112, 34))
        self.btn_plot.setObjectName(_fromUtf8("btn_plot"))
        self.lbl_select_variable_label = QtGui.QLabel(self.results_review)
        self.lbl_select_variable_label.setGeometry(QtCore.QRect(10, 60, 121, 19))
        self.lbl_select_variable_label.setObjectName(_fromUtf8("lbl_select_variable_label"))
        self.cmb_select_variable = QtGui.QComboBox(self.results_review)
        self.cmb_select_variable.setGeometry(QtCore.QRect(130, 60, 201, 25))
        self.cmb_select_variable.setObjectName(_fromUtf8("cmb_select_variable"))

        self.gbx_plot_type = QtGui.QGroupBox(self.results_review)
        self.gbx_plot_type.setGeometry(QtCore.QRect(10, 270, 321, 71))
        self.gbx_plot_type.setObjectName(_fromUtf8("gbx_plot_type"))
        self.rdbtn_bar_chart = QtGui.QRadioButton(self.gbx_plot_type)
        self.rdbtn_bar_chart.setGeometry(QtCore.QRect(10, 30, 119, 23))
        self.rdbtn_bar_chart.setObjectName(_fromUtf8("rdbtn_bar_chart"))
        self.rdbtn_line_chart = QtGui.QRadioButton(self.gbx_plot_type)
        self.rdbtn_line_chart.setGeometry(QtCore.QRect(120, 30, 119, 23))
        self.rdbtn_line_chart.setObjectName(_fromUtf8("rdbtn_line_chart"))
        self.gbx_plot_period = QtGui.QGroupBox(self.results_review)
        self.gbx_plot_period.setGeometry(QtCore.QRect(10, 100, 321, 151))
        self.gbx_plot_period.setObjectName(_fromUtf8("gbx_plot_period"))
        self.horizontalSlider = QtGui.QSlider(self.gbx_plot_period)
        self.horizontalSlider.setGeometry(QtCore.QRect(10, 60, 301, 22))
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setObjectName(_fromUtf8("horizontalSlider"))
        self.horizontalSlider_2 = QtGui.QSlider(self.gbx_plot_period)
        self.horizontalSlider_2.setGeometry(QtCore.QRect(10, 120, 301, 22))
        self.horizontalSlider_2.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_2.setObjectName(_fromUtf8("horizontalSlider_2"))
        self.lbl_start_year = QtGui.QLabel(self.gbx_plot_period)
        self.lbl_start_year.setGeometry(QtCore.QRect(10, 30, 68, 19))
        self.lbl_start_year.setObjectName(_fromUtf8("lbl_start_year"))
        self.lbl_end_year = QtGui.QLabel(self.gbx_plot_period)
        self.lbl_end_year.setGeometry(QtCore.QRect(10, 90, 68, 19))
        self.lbl_end_year.setObjectName(_fromUtf8("lbl_end_year"))
        
        self.tab_controlpanel.addTab(self.results_review, _fromUtf8(""))


        self.data_analysis = QtGui.QWidget()
        self.data_analysis.setObjectName(_fromUtf8("data_analysis"))
        self.btn_plot_2 = QtGui.QPushButton(self.data_analysis)
        self.btn_plot_2.setGeometry(QtCore.QRect(110, 580, 112, 34))
        self.btn_plot_2.setObjectName(_fromUtf8("btn_plot_2"))
        self.gbx_cross_section_ana = QtGui.QGroupBox(self.data_analysis)
        self.gbx_cross_section_ana.setGeometry(QtCore.QRect(10, 20, 321, 211))
        self.gbx_cross_section_ana.setObjectName(_fromUtf8("gbx_cross_section_ana"))
        self.cmb_select_variable_2 = QtGui.QComboBox(self.gbx_cross_section_ana)
        self.cmb_select_variable_2.setGeometry(QtCore.QRect(130, 70, 181, 25))
        self.cmb_select_variable_2.setObjectName(_fromUtf8("cmb_select_variable_2"))
        self.cmb_select_scenario_2 = QtGui.QComboBox(self.gbx_cross_section_ana)
        self.cmb_select_scenario_2.setGeometry(QtCore.QRect(130, 30, 181, 25))
        self.cmb_select_scenario_2.setObjectName(_fromUtf8("cmb_select_scenario_2"))
        self.lbl_select_variable_label_2 = QtGui.QLabel(self.gbx_cross_section_ana)
        self.lbl_select_variable_label_2.setGeometry(QtCore.QRect(10, 70, 121, 19))
        self.lbl_select_variable_label_2.setObjectName(_fromUtf8("lbl_select_variable_label_2"))
        self.lbl_select_scenario_label_2 = QtGui.QLabel(self.gbx_cross_section_ana)
        self.lbl_select_scenario_label_2.setGeometry(QtCore.QRect(10, 30, 121, 19))
        self.lbl_select_scenario_label_2.setObjectName(_fromUtf8("lbl_select_scenario_label_2"))
        self.lbl_select_year_label = QtGui.QLabel(self.gbx_cross_section_ana)
        self.lbl_select_year_label.setGeometry(QtCore.QRect(10, 110, 121, 19))
        self.lbl_select_year_label.setObjectName(_fromUtf8("lbl_select_year_label"))
        self.sbx_select_year_spinbox = QtGui.QSpinBox(self.gbx_cross_section_ana)
        self.sbx_select_year_spinbox.setGeometry(QtCore.QRect(160, 110, 151, 25))
        self.sbx_select_year_spinbox.setObjectName(_fromUtf8("sbx_select_year_spinbox"))
        self.rdbtn_histogram = QtGui.QRadioButton(self.gbx_cross_section_ana)
        self.rdbtn_histogram.setGeometry(QtCore.QRect(10, 160, 119, 23))
        self.rdbtn_histogram.setObjectName(_fromUtf8("rdbtn_histogram"))
        self.gbx_time_series_ana = QtGui.QGroupBox(self.data_analysis)
        self.gbx_time_series_ana.setGeometry(QtCore.QRect(10, 250, 321, 291))
        self.gbx_time_series_ana.setObjectName(_fromUtf8("gbx_time_series_ana"))
        self.cmb_select_variable_3 = QtGui.QComboBox(self.gbx_time_series_ana)
        self.cmb_select_variable_3.setGeometry(QtCore.QRect(130, 70, 181, 25))
        self.cmb_select_variable_3.setObjectName(_fromUtf8("cmb_select_variable_3"))
        self.cmb_select_scenario_3 = QtGui.QComboBox(self.gbx_time_series_ana)
        self.cmb_select_scenario_3.setGeometry(QtCore.QRect(130, 30, 181, 25))
        self.cmb_select_scenario_3.setObjectName(_fromUtf8("cmb_select_scenario_3"))
        self.lbl_select_variable_label_3 = QtGui.QLabel(self.gbx_time_series_ana)
        self.lbl_select_variable_label_3.setGeometry(QtCore.QRect(10, 70, 121, 19))
        self.lbl_select_variable_label_3.setObjectName(_fromUtf8("lbl_select_variable_label_3"))
        self.lbl_select_scenario_label_3 = QtGui.QLabel(self.gbx_time_series_ana)
        self.lbl_select_scenario_label_3.setGeometry(QtCore.QRect(10, 30, 121, 19))
        self.lbl_select_scenario_label_3.setObjectName(_fromUtf8("lbl_select_scenario_label_3"))
        self.lbl_select_start_year_label = QtGui.QLabel(self.gbx_time_series_ana)
        self.lbl_select_start_year_label.setGeometry(QtCore.QRect(10, 110, 121, 19))
        self.lbl_select_start_year_label.setObjectName(_fromUtf8("lbl_select_start_year_label"))
        self.sbx_select_year_spinbox_2 = QtGui.QSpinBox(self.gbx_time_series_ana)
        self.sbx_select_year_spinbox_2.setGeometry(QtCore.QRect(160, 110, 151, 25))
        self.sbx_select_year_spinbox_2.setObjectName(_fromUtf8("sbx_select_year_spinbox_2"))
        self.lbl_select_end_year_label = QtGui.QLabel(self.gbx_time_series_ana)
        self.lbl_select_end_year_label.setGeometry(QtCore.QRect(10, 140, 121, 19))
        self.lbl_select_end_year_label.setObjectName(_fromUtf8("lbl_select_end_year_label"))
        self.sbx_select_year_spinbox_3 = QtGui.QSpinBox(self.gbx_time_series_ana)
        self.sbx_select_year_spinbox_3.setGeometry(QtCore.QRect(160, 140, 151, 25))
        self.sbx_select_year_spinbox_3.setObjectName(_fromUtf8("sbx_select_year_spinbox_3"))
        self.rdbtn_stacked_bars_chart = QtGui.QRadioButton(self.gbx_time_series_ana)
        self.rdbtn_stacked_bars_chart.setGeometry(QtCore.QRect(10, 200, 121, 23))
        self.rdbtn_stacked_bars_chart.setObjectName(_fromUtf8("rdbtn_stacked_bars_chart"))
        self.rdbtn_multiple_line_chart = QtGui.QRadioButton(self.gbx_time_series_ana)
        self.rdbtn_multiple_line_chart.setGeometry(QtCore.QRect(160, 200, 131, 23))
        self.rdbtn_multiple_line_chart.setObjectName(_fromUtf8("rdbtn_multiple_line_chart"))
        self.tab_controlpanel.addTab(self.data_analysis, _fromUtf8(""))



        frm_SEEMS_main.setCentralWidget(self.centralwidget)
         
        self.menubar = QtGui.QMenuBar(frm_SEEMS_main)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1070, 31))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setObjectName(_fromUtf8("menuFile"))
        frm_SEEMS_main.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(frm_SEEMS_main)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        frm_SEEMS_main.setStatusBar(self.statusbar)
        self.actionAbout = QtGui.QAction(frm_SEEMS_main)
        self.actionAbout.setObjectName(_fromUtf8("actionAbout"))                
        self.menuFile.addAction(self.actionAbout)
        self.menubar.addAction(self.menuFile.menuAction())

#         # Test color picker button
#         self.btn_color = QtGui.QPushButton(self.results_review)
#         self.btn_color.setGeometry(QtCore.QRect(110, 500, 112, 34))
#         self.btn_color.setObjectName(_fromUtf8("btn_color"))
#         self.btn_color.clicked.connect(self.on_btn_color_clicked)
    
        self.retranslateUi(frm_SEEMS_main)
        self.tab_controlpanel.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(frm_SEEMS_main)
    
    
        '''
        The following lines in this submodule are developers added codes
        '''

        # Setup the progress bar in the GUI
        self.prb_progressBar.setMinimum(0)
        self.prb_progressBar.setMaximum(simulation_depth * 100)        
 
        # Create another QWidget within frm_SEEMS_main to host the matplotlib canvas
        self.canvaswidget = QtGui.QWidget(frm_SEEMS_main)
        self.canvaswidget.setObjectName(_fromUtf8("canvaswidget"))
        self.canvaswidget.setGeometry(QtCore.QRect(390, 50, 661, 661))
              
        # Create a QVBoxLayout within the canvas widget, such that the canvas embeds in the main window frame
        self.lyt = QtGui.QVBoxLayout(self.canvaswidget)

        # Create a canvas instance
        self.mc = MplCanvas(self.canvaswidget)

        '''
        #         Another way to create a canvas, without introducing a seperately defined class
        #         # create a canvas
        #         fig = Figure()        
        #         self.mc = FigureCanvas(fig)
        # 
        #         self.mc.axes = fig.add_subplot(111)
        #         self.mc.axes.hold(True) 
        # 
        #         self.mc.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        #         self.mc.updateGeometry()          
        '''


        # Create a matplotlib toolbar
        self.mpl_toolbar = NavigationToolbar(self.mc, self.canvaswidget)        
            
        # Add the canvas and toolbar instances into the VBox Layout
        self.lyt.addWidget(self.mc)        
        self.lyt.addWidget(self.mpl_toolbar)
        
        # Initiate the results review and data analysis panels
        refresh_review_panel(self)
        refresh_analysis_panel(self)
 
  
        # Events handling 
        self.btn_plot.clicked.connect(self.on_btn_plot_clicked)
        self.btn_plot_2.clicked.connect(self.on_btn_plot_2_clicked)
         
        self.btn_start_simulation.clicked.connect(self.on_btn_start_simulation_clicked)
        
        

  
  
    def retranslateUi(self, frm_SEEMS_main):
        frm_SEEMS_main.setWindowTitle(_translate("frm_SEEMS_main", "SEEMS  -  Socio-Economical-Ecological Multipurpose Simulator", None))
        self.btn_start_simulation.setText(_translate("frm_SEEMS_main", "Start Simulation", None))
        self.lbl_input_scenario_name_label.setText(_translate("frm_SEEMS_main", "Scenario Name:", None))
        self.tab_controlpanel.setTabText(self.tab_controlpanel.indexOf(self.scenarios_setup), _translate("frm_SEEMS_main", "Scenarios Setup", None))

        self.lbl_select_scenario_label.setText(_translate("frm_SEEMS_main", "Select Scenario:", None))
        self.btn_plot.setText(_translate("frm_SEEMS_main", "Plot", None))
        self.lbl_select_variable_label.setText(_translate("frm_SEEMS_main", "Select Variable:", None))
        self.gbx_plot_type.setTitle(_translate("frm_SEEMS_main", "Plot Type", None))
        self.rdbtn_bar_chart.setText(_translate("frm_SEEMS_main", "Bar Chart", None))
        self.rdbtn_line_chart.setText(_translate("frm_SEEMS_main", "Line Chart", None))
        self.gbx_plot_period.setTitle(_translate("frm_SEEMS_main", "Plot Period", None))
        self.lbl_start_year.setText(_translate("frm_SEEMS_main", "Start Year", None))
        self.lbl_end_year.setText(_translate("frm_SEEMS_main", "End Year", None))
        self.tab_controlpanel.setTabText(self.tab_controlpanel.indexOf(self.results_review), _translate("frm_SEEMS_main", "Results Review", None))

        self.btn_plot_2.setText(_translate("frm_SEEMS_main", "Plot", None))
        self.gbx_cross_section_ana.setTitle(_translate("frm_SEEMS_main", "Cross-section Data Analysis", None))
        self.lbl_select_variable_label_2.setText(_translate("frm_SEEMS_main", "Select Variable:", None))
        self.lbl_select_scenario_label_2.setText(_translate("frm_SEEMS_main", "Select Scenario:", None))
        self.lbl_select_year_label.setText(_translate("frm_SEEMS_main", "Select Year:", None))
        self.rdbtn_histogram.setText(_translate("frm_SEEMS_main", "Histogram", None))
        self.gbx_time_series_ana.setTitle(_translate("frm_SEEMS_main", "Time-series Data Analysis", None))
        self.lbl_select_variable_label_3.setText(_translate("frm_SEEMS_main", "Select Variable:", None))
        self.lbl_select_scenario_label_3.setText(_translate("frm_SEEMS_main", "Select Scenario:", None))
        self.lbl_select_start_year_label.setText(_translate("frm_SEEMS_main", "Select Start Year:", None))
        self.lbl_select_end_year_label.setText(_translate("frm_SEEMS_main", "Select End Year:", None))
        self.rdbtn_stacked_bars_chart.setText(_translate("frm_SEEMS_main", "Stacked Bars", None))
        self.rdbtn_multiple_line_chart.setText(_translate("frm_SEEMS_main", "Multiple Lines", None))
        self.tab_controlpanel.setTabText(self.tab_controlpanel.indexOf(self.data_analysis), _translate("frm_SEEMS_main", "Data Analysis", None))
        
        self.menuFile.setTitle(_translate("frm_SEEMS_main", "Help", None))
        self.actionAbout.setText(_translate("frm_SEEMS_main", "About", None))

        
        
#         # Test button color picker
#         self.btn_color.setText(_translate("frm_SEEMS_main", "Color", None))


    def on_btn_start_simulation_clicked(self):
        
        # Set up the scenario name from the LineEdit box in the GUI
        # Should check for already existing names, otherwise later results will be added to the existing table, causing troubles

        scenario_name = str(self.txt_input_scenario_name.text())
                  
        # Run the simulation
        create_scenario(db, scenario_name, model_table_name, model_table, household_table_name, household_table, 
                        person_table_name, person_table, land_table_name, land_table, 
                        business_sector_table_name, business_sector_table, policy_table_name, policy_table, 
                        stat_table_name, stat_table, simulation_depth, start_year, end_year, self)
      
        # Show a message box indicating the completion of run.
        msb = QMessageBox()
        msb.setText('The Simulation is Complete!        ')
        msb.setWindowTitle('SEEMS Run')
        msb.exec_()



    def on_btn_plot_2_clicked(self):
        '''
        The Plot button in the 'Data Analysis' Tag of the Control Panel
        '''
        
        # Read the statistics table and make the lists for plotting charts        
        stat_table = DataAccess.get_table(db, stat_table_name)

        # Set the plot title
        plot_title = str(self.cmb_select_variable_3.currentText())
        
        # Define temporary variables
        time_stamps = list()
                
        total_agriculture_income = list()
        total_temp_job_income = list()
        total_freight_trans_income = list()
        total_passenger_trans_income = list()
        total_lodging_income =  list()
        total_renting_income = list()


        # Get the series to be plot from the combo box selection
        if str(self.cmb_select_variable_3.currentText()) == 'Sectors_Income_Structure':
        
            # Assign values for the variable lists
            for st in stat_table:            
                # Look only the records for the current scenario version
                if st.ScenarioVersion == self.cmb_select_scenario_3.currentText():                                 
                    if st.Variable == 'Total_Agriculture_Income':
                        time_stamps.append(st.StatDate)                    
                        total_agriculture_income.append(st.StatValue)
                        agri_tuple = (st.Variable, total_agriculture_income)
                    
                    elif st.Variable == 'Total_Temp_Job_Income':
                        total_temp_job_income.append(st.StatValue)
                        temj_tuple = (st.Variable, total_temp_job_income)
                    
                    elif st.Variable == 'Total_Freight_Trans_Income':
                        total_freight_trans_income.append(st.StatValue)
                        frtt_tuple = (st.Variable, total_freight_trans_income)
                    
                    elif st.Variable == 'Total_Passenger_Trans_Income':
                        total_passenger_trans_income.append(st.StatValue)
                        pagt_tuple = (st.Variable, total_passenger_trans_income)
                    
                    elif st.Variable == 'Total_Lodging_Income':
                        total_lodging_income.append(st.StatValue)
                        ldgg_tuple = (st.Variable, total_lodging_income)
                    
                    elif st.Variable == 'Total_Renting_Income':
                        total_renting_income.append(st.StatValue)
                        rent_tuple = (st.Variable, total_renting_income)
            
            plot_series_list = [agri_tuple, temj_tuple, frtt_tuple, pagt_tuple, ldgg_tuple, rent_tuple]


        # Draw the plot
        # First, remove any existing canvas contents
        self.lyt.removeWidget(self.mc)
        self.lyt.removeWidget(self.mpl_toolbar)
        
        # Then create a new canvas instance
        self.mc = MplCanvas(self.canvaswidget)
        self.mc.plot('timeseries', time_stamps, plot_series_list, plot_title, self)




    def on_btn_plot_clicked(self):
        '''
        The Plot button in the 'Results Review' Tag of the Control Panel
        '''
        
        # Note that data must be read from the database, rather than lists and dictionaries in the program, 
        # for users may need to make plots after the iteration (running of main simulation program).
        
        # Read the statistics table and make the lists for plotting charts        
        stat_table = DataAccess.get_table(db, stat_table_name)
        
        # Define the x_data (time_stamps list) and y_data (series list)
        time_stamps = list()
        series = list()

        plot_title = str(self.cmb_select_variable.currentText())
        
        # Assign values for the variable lists
        for st in stat_table:            
            # Look only the records for the current scenario version
            if st.ScenarioVersion == self.cmb_select_scenario.currentText():       
                if st.Variable == str(self.cmb_select_variable.currentText()):
                    time_stamps.append(st.StatDate)
                    series_name = st.Variable
                    series.append(st.StatValue)
                    
        plot_series_list = [(series_name, series)]            

        # Draw the plot
        # First, remove any existing canvas contents
        self.lyt.removeWidget(self.mc)
        self.lyt.removeWidget(self.mpl_toolbar)
        
        # Then create a new canvas instance
        self.mc = MplCanvas(self.canvaswidget)
        self.mc.plot('timeseries', time_stamps, plot_series_list, plot_title, self)

        

    

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure()
        self.axes = fig.add_subplot(111)
        
        # Set if the axes is cleared every time plot() is called.
        self.axes.hold(True)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


    def plot(self, data_type, x_data, y_data, plot_title, gui):
        '''
        Make a plot.
        
        data_type = crosssection/timeseries
        x_data: a simple list of numbers
        y_data: a list of tuples; each tuple is in the form of (series_name, [series_data_list]).
        plot_title: the title of the plot.
        
        '''

        if data_type == 'timeseries':

            # Determine the chart type
            if gui.rdbtn_bar_chart.isChecked() and gui.tab_controlpanel.currentIndex() == 1 \
            or gui.rdbtn_stacked_bars_chart.isChecked() and gui.tab_controlpanel.currentIndex() == 2:                
                for i in range(len(y_data)):
                    if i == 0:
                        accu_series= numpy.subtract(y_data[i][1], y_data[i][1]) 
                    else:
                        accu_series= numpy.add(accu_series, y_data[i - 1][1]) 
                    
                    self.axes.bar(x_data, y_data[i][1], bottom = accu_series, color = numpy.random.rand(3,1), label = y_data[i][0])                        
                            
                self.axes.set_title(plot_title)
                self.axes.legend(loc = 2)
                self.axes.set_xlabel('Year')
        #         self.axes.set_xticklabels(time_stamps)
        #         self.axes.set_ylabel('Income/RMB')
                
            elif gui.rdbtn_line_chart.isChecked() and gui.tab_controlpanel.currentIndex() == 1 \
            or gui.rdbtn_multiple_line_chart.isChecked() and gui.tab_controlpanel.currentIndex() == 2:
                for i in range(len(y_data)):                    
                    self.axes.plot(x_data, y_data[i][1], color = numpy.random.rand(3,1), label = y_data[i][0])                        
                            
                self.axes.set_title(plot_title)
                self.axes.legend(loc = 2)
                self.axes.set_xlabel('Year')

                 
            else: # Bar chart by default
                for i in range(len(y_data)):
                    if i == 0:
                        accu_series= numpy.subtract(y_data[i][1], y_data[i][1]) 
                    else:
                        accu_series= numpy.add(accu_series, y_data[i - 1][1]) 
                     
                    self.axes.bar(x_data, y_data[i][1], bottom = accu_series, color = numpy.random.rand(3,1), label = y_data[i][0])                        
                             
                self.axes.set_title(plot_title)
                self.axes.legend(loc = 2)
                self.axes.set_xlabel('Year')
        
        
        elif data_type == 'crosssection':
            pass
        


        # Create a new toolbar
        gui.mpl_toolbar = NavigationToolbar(gui.mc, gui.canvaswidget)

        # Add the widegts to the vbox
        gui.lyt.addWidget(gui.mc)
        gui.lyt.addWidget(gui.mpl_toolbar)


