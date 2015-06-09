'''
Created on Mar 26, 2015

@author: Liyan Xu; Hongmou Zhang
'''
import copy
import random

from data_access import DataAccess
from household import Household
# from person import Person
from capital_property import *
from land import *
from business_sector import *
from policy import Policy


class Society(object):
    '''
    This is the definition of society class
    
    Create the household, person, statistics, etc. dictionaries.
    Load model parameters, business sectors information, etc.
    '''


    def __init__(self, db, model_table_name, model_table, hh_table_name, hh_table, pp_table_name, pp_table, 
                 land_table_name, land_table, business_sector_table_name, business_sector_table, 
                 policy_table_name, policy_table, stat_table_name, stat_table, simulation_depth, start_year):
        '''
        Initialize the society class;
        '''
        
        # Set the current time stamp
        self.current_year = start_year
        
        # Create a dictionary to store model parameters, indexed by Variable_Name, and contents are Variable_Value      
        self.model_parameters_dict = dict()        
        # Fill in the model parameters dictionary from the model table (fetched from DB)
        for record in model_table:
            self.model_parameters_dict[record.Variable_Name] = record.Variable_Value
          
        
        # Get the variable lists for household, person, land, business sector, policy, and statistics classes 
        self.hh_var_list = DataAccess.get_var_list(db, hh_table_name)
        self.pp_var_list = DataAccess.get_var_list(db, pp_table_name)
        self.land_var_list = DataAccess.get_var_list(db, land_table_name)
        self.business_sector_var_list = DataAccess.get_var_list(db, business_sector_table_name)
        self.policy_var_list = DataAccess.get_var_list(db, policy_table_name)
        self.stat_var_list = DataAccess.get_var_list(db, stat_table_name)


        # Initialize the household instances;
        # And create a dictionary to store them, indexed by HID.
        self.hh_dict = dict()        
        # Add household instances to hh_dict
        for hh in hh_table:
            hh_temp = Household(hh, self.hh_var_list, self.current_year, db, pp_table_name, pp_table, 
                                self.model_parameters_dict)
            self.hh_dict[hh_temp.HID] = hh_temp # Indexed by HID
        
        
        # Initialize the land instances, and create a land dictionary to store all the land parcels
        # Note that the land parcels here do not necessarily belong to any household. i.e. land_parcel.HID could be "None".
        self.land_dict = dict()
        for land in land_table:
            land_parcel = Land(land, self.land_var_list, self.current_year)
            self.land_dict[land_parcel.OBJECTID_1] = land_parcel
        
        # Then allocate the parcels with an HID to the respective household's own_capital_properties.land_properties_list.
        for OBJECTID_1 in self.land_dict:
            for HID in self.hh_dict:
                if self.land_dict[OBJECTID_1].HID == HID:
                    self.hh_dict[HID].own_capital_properties.land_properties_list.append(self.land_dict[OBJECTID_1])

       
        
        # Initialize the business sector instances;
        # And create a dictionary to store them, indexed by sector name.
        self.business_sector_dict = dict()
        for sector in business_sector_table:
            sector_temp = BusinessSector(sector, self.business_sector_var_list)
            self.business_sector_dict[sector_temp.SectorName] = sector_temp # Indexed by SectorName
            
        
        # Initialize the policy program instances;
        # And create a dictionary to store them, indexed by policy program type.
        self.policy_dict = dict()
        for program in policy_table:
            program_temp = Policy(program, self.policy_var_list)
            self.policy_dict[program_temp.PolicyType] = program_temp
        
                        
        # Create a statistics dictionary; indexed by Variable Names.To be filled later in Statistics Class.
        self.stat_dict = dict()
        
        
        # Counters for debugging
        self.count = 0
        self.count1 = 0
        self.count2 = 0
        
        
    
        
    




        
    def step_go(self, start_year, iteration_count):
        '''
        (Annual) iterative activities of the society class' instance.
        '''
        
        # Update the current year tag
        self.current_year = start_year + iteration_count + 1
                     
        # Then do the followings step by step
        self.agents_update()
         
        self.marriage()
          
        self.child_birth()
        
        
        self.household_capital_property_update()
                
        self.household_economy()
        
        
        self.land_update()
        
        # Debugging code
        print self.count2, self.count1, self.count
        



    
    def household_economy(self):
        
        for HID in self.hh_dict:
            # Determine the household's preferences
            self.hh_dict[HID].housedhold_categorization()
            
            # Determine which policy program to participate in
            self.hh_dict[HID].household_policy_decision(self.policy_dict, self.business_sector_dict, self.model_parameters_dict)
        
            # Do the business
            # The second parameter, risk_effective = True, indicating it is a "real world" run this time,
            # as opposed to the two "hypothetical" runs in the previous step, the policy decision step,
            # when risk_effective = False. i.e. random factors don't take effect in households' economy decision-making process.
            self.hh_dict[HID].own_capital_properties = self.hh_dict[HID].household_business_revenue(self.hh_dict[HID].own_capital_properties, self.business_sector_dict, True, self.model_parameters_dict)
            
            # Household's final accounting for the year
            self.hh_dict[HID].household_final_accounting(self.model_parameters_dict)

    
    
    def land_update(self):
        
        # Deal with the reverted farmland first
        for HID in self.hh_dict:
            for land_parcel in self.hh_dict[HID].own_capital_properties.land_properties_list:
                if land_parcel.IsG2G_this_year == True:
                    self.hh_dict[HID].own_capital_properties.land_properties_list.remove(land_parcel)
                        
                # And change the attributes of the same land parcel in society.land_dict
                self.land_dict[land_parcel.OBJECTID_1].IsG2G = 1
                self.land_dict[land_parcel.OBJECTID_1].SStartyear = self.current_year
                self.land_dict[land_parcel.OBJECTID_1].HID = ''
        
        # Then simulate the natural land cover succession process
        for OBJECTID_1 in self.land_dict:
            self.land_dict[OBJECTID_1].land_cover_succession(self.current_year, self.model_parameters_dict)
            
               
            
    def agents_update(self):
        '''
        Update household(and person)'s demographic status; do everything except for marriage and child birth.
        '''
        
        temp_hh_list = list()
        
        # Annual household status update
        for HID in self.hh_dict:
            temp_hh_list.append(Household.household_demographic_update(self.hh_dict[HID], self.current_year, self.model_parameters_dict))

        # Reset the households dict
        self.hh_dict = dict()
        
        # Refresh hh_dict
        for h in temp_hh_list:
            self.hh_dict[h.HID] = h
            
            if h.is_exist == 0:
                # Dissolve non-existing households
                if h.is_dissolved_this_year == True:
                    self.dissolve_household(h.HID)                               

            

    
    def marriage(self):
        
        marry_list = list()
        
        # Get the "to be married this year" list
        for HID in self.hh_dict:
            for PID in self.hh_dict[HID].own_pp_dict:
                p = self.hh_dict[HID].own_pp_dict[PID]
                
                if p.is_married_this_year == True:
                    marry_list.append(p)
                    
        # Make matches
        for pp in marry_list:            
            if pp.is_married_this_year == True:
                # Reset the markers
                found = False
                new_hh = False            
                                
                                    
                if pp.Gender == 1: #Male                
                    # Find him a spouse
                    for sp in marry_list:
                                        
                        if sp.Gender == 0 and pp.HID != sp.HID and sp.is_married_this_year == True: # spouse must be a female and from a different household
                            # Make the match     
                            pp.is_married_this_year = False
                            sp.is_married_this_year = False # Remove the two persons from the "to be married" list
                            
                            found = True
                            break
                    
                    if found == True:
                        pp.IsMarry = 1
                        sp.IsMarry = 1                                                                               
                        pp.SpouseID = sp.PID
                        sp.SpouseID = pp.PID
                                                
                        # Determine whether to establish a new household                
                        siblings = self.get_siblings(pp)
                                
                        if len(siblings) != 0:
                            for sib in siblings:
                                if sib.HID == pp.HID and sib.Age < pp.Age: # If pp has any younger brothers in his household
                                    new_hh = True # Then establish a new household
                            
                        # Assign household affiliation for the new couple 
                        if new_hh == True:                                        
                            # Create a new household with the male pp being the household head
                            self.create_new_household(pp)
                            self.add_person_to_household(sp, pp.HID, 'spouse') # Add sp to the newly created household as pp's spouse
                            
                            # Modify the FatherID/MotherID of any children of pp and sp
                            # And if either one of the new couple has any unmarried children, add them into the new household
                            # Father
                            if self.get_children(pp) is not None:
                                for kid in self.get_children(pp):
                                    kid.MotherID = sp.PID        
                                                                
                                    if kid.IsMarry == 0:
                                        self.add_person_to_household(kid, pp.HID, 'non_newborn_kid')

                            # Mother                         
                            if self.get_children(sp) is not None:
                                for kid in self.get_children(sp):
                                    kid.FatherID = pp.PID
                                    
                                    if kid.IsMarry == 0:
                                        self.add_person_to_household(kid, pp.HID, 'non_newborn_kid')
                                                                               
                        else:
                            self.add_person_to_household(sp, pp.HID, 'spouse')
                            # If the female sp has any children, add them into the new household
                            if self.get_children(sp) is not None:
                                for kid in self.get_children(sp):
                                    kid.FatherID = pp.PID
                                    
                                    if kid.IsMarry == 0:
                                        self.add_person_to_household(kid, pp.HID, 'non_newborn_kid')
                                                            
                    else:
                        # If failed to find a match    
                        pp.is_married_this_year = False                        
                            

                                    
                                              
                else: #Female
                    # Find her a spouse       
                    for sp in marry_list:
    
                        if sp.Gender == 1 and pp.HID != sp.HID and sp.is_married_this_year == True: # spouse must be a female and from a different household
                            # Make the match                    
                            pp.is_married_this_year = False
                            sp.is_married_this_year = False # Remove the two persons from the "to be married" list

                            found = True
                            break
                        
                    if found == True:                    
                        pp.IsMarry = 1
                        sp.IsMarry = 1 
                        pp.SpouseID = sp.PID
                        sp.SpouseID = pp.PID             
                                   
                        # Determine whether to establish a new household                
                        siblings = self.get_siblings(sp)
                                
                        if len(siblings) != 0:
                            for sib in siblings:
                                if sib.HID == sp.HID and sib.Age < sp.Age: # If pp has any younger brothers in his household
                                    new_hh = True # Then establish a new household

                        # Assign household affiliation for the new couple 
                        if new_hh == True:                                        
                            # Create a new household with the male sp being the household head
                            self.create_new_household(sp)
                            self.add_person_to_household(pp, sp.HID, 'spouse') # # Add pp to the newly created household as sp's spouse
                            
                            # Modify the FatherID/MotherID of any children of pp and sp
                            # And if either one of the new couple has any unmarried children, add them into the new household
                            # Mother
                            if self.get_children(pp) is not None:
                                for kid in self.get_children(pp):
                                    kid.FatherID = sp.PID                                    
                                    
                                    if kid.IsMarry == 0:
                                        self.add_person_to_household(kid, sp.HID, 'non_newborn_kid')

                                                    
                            # Father                         
                            if self.get_children(sp) is not None:
                                for kid in self.get_children(sp):
                                    kid.MotherID = pp.PID
                                    
                                    if kid.IsMarry == 0:                                    
                                        self.add_person_to_household(kid, sp.HID, 'non_newborn_kid')
                                        
                        else:
                            self.add_person_to_household(pp, sp.HID, 'spouse')
                            # If the female pp has any children, add them into the new household
                            if self.get_children(pp) is not None:
                                for kid in self.get_children(sp):
                                    kid.FatherID = sp.PID
                                    
                                    if kid.IsMarry == 0:
                                        self.add_person_to_household(kid, sp.HID, 'non_newborn_kid')
                        
                    else:
                        # If failed to find a match    
                        pp.is_married_this_year = False                             
                            



    
    def child_birth(self):
        
        mom_list = list()
        
        for HID in self.hh_dict:
            for PID in self.hh_dict[HID].own_pp_dict:
                pp = self.hh_dict[HID].own_pp_dict[PID]
                
                if pp.is_giving_birth_this_year == True:
                    mom_list.append(pp)
                
        for mom in mom_list:
            new_baby = self.create_new_person(mom)
            self.add_person_to_household(new_baby, mom.HID, 'newborn_kid')




    def household_capital_property_update(self):
        '''
        Traverse the hh_dict. Update every existing household's capital properties status.
        '''
        
        for HID in self.hh_dict:
            hh = self.hh_dict[HID]
            
            if hh.is_exist == 1:
                # Only deal with existing households
                hh.own_capital_properties.refresh(hh)




    def create_new_person(self, mom):
        '''
        Create a person instance with mom being its mother.
        Note that the only occasion when a new person instance is created is the birth of a new baby.
        '''

        new_pp = copy.deepcopy(mom)

        # Reset all properties
        for var in new_pp.pp_var_list:
            setattr(new_pp, var[0], None)       
            
        # Grant new properties
        new_pp.HID = mom.HID
        new_pp.Hname = mom.Hname
        
        new_pp.PID = self.assign_new_pid(mom)
        new_pp.Pname = mom.Pname + 'c'

        new_pp.Gender = self.assign_gender()
        new_pp.Age = 0
        new_pp.R2HHH = self.get_relation_to_hh_head(new_pp, 'child')
        new_pp.IsMarry = 0

        new_pp.MotherID = mom.PID
        new_pp.FatherID = mom.SpouseID
        new_pp.SpouseID = '0'
        
        new_pp.Education = 'uneducated'
#         new_pp.Ethnicity = self.cur_pp_dict[mom.SpouseID].Ethnicity
        
        new_pp.is_alive = 1
        
        
        new_pp.is_college = False
        new_pp.moved_out = False     
        new_pp.marriage_length = 0
                
        new_pp.is_married_this_year = False   
        new_pp.is_giving_birth_this_year = False
        new_pp.is_died_this_year = False
        
        new_pp.StatDate = self.current_year

        return new_pp
    
    
    
    
    
    
    def create_new_household(self, pp):
        '''
        Create a new household instance and grant it assign the attributes values.
        '''

        # Make a new household instance through deepcopy
        new_hh = copy.deepcopy(self.hh_dict[pp.HID])     
         
        # Record the original HID
        ori_hid = pp.HID
         
        # Reset all household properties, clear own_pp_dict, and reset the own_capital_properties instance
        for var in new_hh.hh_var_list:
            setattr(new_hh, var[0], None)        

        new_hh.own_pp_dict = dict()
        
        # Reset household's capital properties
        for item in new_hh.own_capital_properties.__dict__:
            if item != 'land_properties_list':
                new_hh.own_capital_properties.__dict__[item] = 0
            else:
                new_hh.own_capital_properties.land_properties_list = list()
            
        
        # Assign a new HID for the new household
        new_hh.HID = self.assign_new_hid(pp)
         
        # Assign other new household properties
        new_hh.Hname = pp.Pname
        new_hh.StatDate = self.current_year
        new_hh.NonRural = self.hh_dict[ori_hid].NonRural
        new_hh.is_exist = 1
                
        '''
        Temporarily let the new household inherit its parent household's geographic features
        '''
        new_hh.LocType = self.hh_dict[ori_hid].LocType
        new_hh.Elevation = self.hh_dict[ori_hid].Elevation
        new_hh.DistanceFrom303 = self.hh_dict[ori_hid].DistanceFrom303
        
        # Modify the new household head's personal attributes to match the new household
        pp.HID = new_hh.HID
        pp.Hname = new_hh.Hname
        pp.R2HHH = '3_00_1'


        # Remove the new household head (pp) from his original household's persons dict
        del self.hh_dict[ori_hid].own_pp_dict[pp.PID]   
                                          
        # Add the new household head (pp) to new_hh.own_pp_dict
        new_hh.own_pp_dict[pp.PID] = pp
                  
        # Add the newly created household to Society's household dict
        self.hh_dict[new_hh.HID] = new_hh

        # Reallocate capital properties from the original household to the newly created one.
        self.household_property_reallocate(new_hh.HID, ori_hid, 'hh_head')
        



    
    


    
    def add_person_to_household(self, pp, HID, role):
        '''
        Add the person pp into the household with HID = HID.
        role - as what role is the person added into the household: spouse/non_newborn_kid/newborn_kid.
        '''

        if role == 'spouse' or role == 'non_newborn_kid':            
            # Record the original HID
            ori_hid = pp.HID

            # Remove the person from his/her original household's persons dict
            del self.hh_dict[ori_hid].own_pp_dict[pp.PID]          
            
            
            # Modify the personal properties of the newly added person
            pp.HID = HID
            pp.Hname = self.hh_dict[HID].Hname 
            pp.R2HHH = self.get_relation_to_hh_head(pp, 'spouse')       
            
            
            # Add the person to new household's members dict
            self.hh_dict[HID].own_pp_dict[pp.PID] = pp


            if role == 'spouse':
                # if the person is added into the household through marriage and as a spouse (by definition female in this program)
                # reallocate the capital properties between the households
                self.household_property_reallocate(HID, ori_hid, 'spouse')
                
            
            # If the original household then has no members, mark it as non-exist.            
            alive_members_count = 0
            for PID in self.hh_dict[ori_hid].own_pp_dict:
                if self.hh_dict[ori_hid].own_pp_dict[PID].is_alive == 1:
                    alive_members_count += 1            
            
            if alive_members_count == 0:
                self.hh_dict[ori_hid].is_exist = 0 # Such that the original household is dissolved
                
                # Transfer household properties
                CapitalProperty.merge_capital_properties(self.hh_dict[ori_hid].own_capital_properties, self, ori_hid, HID)
                
                # Debugging codes
                self.count2 += 1
            
                        
        
        elif role == 'newborn_kid': # Newborn kids
            # Add the person to household members dict
            self.hh_dict[HID].own_pp_dict[pp.PID] = pp




    
    def dissolve_household(self, HID):
        '''
        Dissolve a household with no live members.
        Only effective when the household is dissolved due to deaths of all its members;
        The other case, when the household is dissolved as a result of marriage, is taken care of in the add_person_to_household submodule.
        '''
                
        # Deal with household properties that were left behind
        self.legacy(HID)
        self.count1 += 1



    def legacy(self, HID):
        '''
        When a household (HID = HID) is dissolved due to deaths of all its members,
        this submodule finds its heir(s) and then allocate its legacy.
        '''
        
        # First, get the last person who lived in the dissolved household ("the ancestor")        
        # Define a list because multiple persons could die in the same year
        ancestor_list = list()                
        for PID in self.hh_dict[HID].own_pp_dict:
            pp = self.hh_dict[HID].own_pp_dict[PID]
            if pp.is_died_this_year == True:
                ancestor_list.append((pp.Age, pp))
                
                # If multiple persons dies within one year, make the oldest one the "ancestor"
                if len(ancestor_list) > 1:
                    ancestor_list.sort(reverse = True) 
        
        # Find the one ancestor
        ancestor = ancestor_list[0][1]

        
        # Then, get the list of potential heirs
        heirs_list = list()
        
        # Add children
        if self.get_children(ancestor) is not None:
            for child in self.get_children(ancestor):
                heirs_list.append(("1_" + str(child.Age), child))
        
        # Add grand-children
        if len(heirs_list) == 0:
            if self.get_children(ancestor) is not None:
                for child in self.get_children(ancestor):
                    if self.get_children(child) is not None:
                        for grandchild in self.get_children(child):
                            if self.get_children(grandchild) is not None:
                                heirs_list.append(("2_" + str(grandchild.Age), grandchild))
 
         
#         # Add grand-grand-children
#         if len(heirs_list) == 0: 
#             if self.get_children(ancestor) is not None:
#                 for child in self.get_children(ancestor):
#                     if self.get_children(child) is not None:
#                         for grandchild in self.get_children(child):
#                             if self.get_children(grandchild) is not None:
#                                 for g_grandchild in self.get_children(grandchild):
#                                     heirs_list.append(("3_" + str(g_grandchild.Age), g_grandchild))
                
        # Add parents
        if len(heirs_list) == 0:
            if self.get_father(ancestor) is not None:
                heirs_list.append(("4_" + str(self.get_father(ancestor).Age), self.get_father(ancestor)))
            if self.get_mother(ancestor) is not None:
                heirs_list.append(("4_" + str(self.get_mother(ancestor).Age), self.get_mother(ancestor)))

             
#         # Add grandparents
#         if len(heirs_list) == 0:
#             if self.get_father(ancestor) is not None:
#                 if self.get_father(self.get_father(ancestor)) is not None:
#                     heirs_list.append(("5_" + str(self.get_father(self.get_father(ancestor)).Age), self.get_father(self.get_father(ancestor))))
#                 if self.get_mother(self.get_father(ancestor)) is not None:
#                     heirs_list.append(("5_" + str(self.get_mother(self.get_father(ancestor)).Age), self.get_mother(self.get_father(ancestor))))
#             if self.get_mother(ancestor) is not None:
#                 if self.get_father(self.get_mother(ancestor)) is not None:
#                     heirs_list.append(("5_" + str(self.get_father(self.get_mother(ancestor)).Age), self.get_father(self.get_mother(ancestor))))
#                 if self.get_mother(self.get_mother(ancestor)) is not None:
#                     heirs_list.append(("5_" + str(self.get_mother(self.get_mother(ancestor)).Age), self.get_mother(self.get_mother(ancestor))))
              
        
        # Add siblings and nephews/nieces
        if len(heirs_list) == 0:
            if self.get_siblings(ancestor) is not None:  # siblings
                for sibling in self.get_siblings(ancestor):
                    heirs_list.append(("6_" + str(sibling.Age), sibling))
                    
#                     nn_list = self.get_children(sibling) # nephews/nieces
#                     if nn_list is not None:
#                         for nn in nn_list:
#                             heirs_list.append(("7_" + str(nn.Age), nn))
            
             
#         # Add cousins
#         if len(heirs_list) == 0:
#             # The father side                        
#             if self.get_father(ancestor) is not None:                
#                 ff_sb_list = self.get_siblings(self.get_father(ancestor)) # Father's siblings list
#                 
#                 if ff_sb_list is not None:
#                     for ff_sb in ff_sb_list:
#                         ff_cs_list = self.get_children(ff_sb) # Cousins from the father side
#                         
#                         if ff_cs_list is not None:
#                             for ff_cs in ff_cs_list:
#                                 heirs_list.append(("8_" + str(ff_cs.Age), ff_cs))
# 
#             # The mother side
#             if self.get_mother(ancestor) is not None:                
#                 mm_sb_list = self.get_siblings(self.get_mother(ancestor)) # Mother's siblings list
#                 
#                 if mm_sb_list is not None:
#                     for mm_sb in mm_sb_list:
#                         mm_cs_list = self.get_children(mm_sb) # Cousins from the mother side
#                         
#                         if mm_cs_list is not None:
#                             for mm_cs in mm_cs_list:
#                                 heirs_list.append(("8_" + str(mm_cs.Age), mm_cs))           
        
                  
    
        # Find the heir and commit the inheritance
        if len(heirs_list) != 0:
            heirs_list.sort()
            heir = heirs_list[0][1]
            
            CapitalProperty.merge_capital_properties(self.hh_dict[HID].own_capital_properties, self, HID, heir.HID)
            
            # Debugging codes
            self.count += 1
            
        else: # Confiscate the legacy
            '''
            to be filled later...
            '''
            pass



    def household_property_reallocate(self, in_HID, out_HID, role):
        '''
        Reallocate capital properties from one household (out_HID) to another (in_HID);
        This only happens when a new household is created through marriage;
        role indicates the party in the marriage. role = hh_head/spouse
        '''
        
        # Get the cost for building a new house for the newly created household
        # adopting a homestead area for 4 persons. 
        new_house_cost = 4 * float(self.model_parameters_dict['HomesteadArea']) * float(self.model_parameters_dict['HomesteadAreaCost'])
        
        if role == 'hh_head':
            
            # First deal with real estate properties
            if self.hh_dict[out_HID].own_capital_properties.cash >= new_house_cost:
                # The parent household can afford the cost for building the new house
                
                # Subtract the building cost from the parent household's cash capitals
                self.hh_dict[out_HID].own_capital_properties.cash = self.hh_dict[out_HID].own_capital_properties.cash - new_house_cost
                
            else:
                # The parent household goes into debt to cover the building costs
                self.hh_dict[out_HID].own_capital_properties.debt = self.hh_dict[out_HID].own_capital_properties.debt + new_house_cost - self.hh_dict[out_HID].own_capital_properties.cash
                self.hh_dict[out_HID].own_capital_properties.cash = 0
                
            # Assign house and homestead properties for the newly created household
            self.hh_dict[in_HID].own_capital_properties.house_area = 4 * float(self.model_parameters_dict['HomesteadArea'])
            self.hh_dict[in_HID].own_capital_properties.house_rooms = int(self.hh_dict[in_HID].own_capital_properties.house_area / float(self.model_parameters_dict['RoomArea']))
            self.hh_dict[in_HID].own_capital_properties.homestead = self.hh_dict[in_HID].own_capital_properties.house_area

            # Then deal with monetary capitals
            transfer = self.hh_dict[out_HID].own_capital_properties.get_monetary_value() / 2
            
            if self.hh_dict[out_HID].own_capital_properties.cash >= transfer:
                self.hh_dict[out_HID].own_capital_properties.cash = self.hh_dict[out_HID].own_capital_properties.cash - transfer
            else:
                self.hh_dict[out_HID].own_capital_properties.cash = 0
                self.hh_dict[out_HID].own_capital_properties.debt = self.hh_dict[out_HID].own_capital_properties.debt + transfer - self.hh_dict[out_HID].own_capital_properties.cash
            
            self.hh_dict[in_HID].own_capital_properties.cash = transfer

        elif role == 'spouse':
            # Just deal with monetary capitals
            transfer = self.hh_dict[in_HID].own_capital_properties.cash # Here the household in_HID is the newly created household and it has been allocated some cash capital in previous steps
            
            if self.hh_dict[out_HID].own_capital_properties.cash >= transfer:
                self.hh_dict[out_HID].own_capital_properties.cash = self.hh_dict[out_HID].own_capital_properties.cash - transfer
            else:
                self.hh_dict[out_HID].own_capital_properties.cash = 0
                self.hh_dict[out_HID].own_capital_properties.debt = self.hh_dict[out_HID].own_capital_properties.debt + transfer - self.hh_dict[out_HID].own_capital_properties.cash
            
            self.hh_dict[in_HID].own_capital_properties.cash += transfer

    
    def assign_new_hid(self, pp):
        '''
        Assign an HID for a newly created household with pp being the head
        '''
        
        group_hid_list = list()
        
        for HID in self.hh_dict: # Must include non-existing hhs, because HIDs are indexed and thus are not allowed to duplicate
            if HID[:5] == pp.HID[:5]: # if the first 5 digits (indicating village and group affiliation) are identical
                group_hid_list.append(HID)
        
        new_id_num = int(max(group_hid_list)[5:])+1
        
        if int(new_id_num/100) != 0: # if the new id number is in hundreds
            new_id = max(group_hid_list)[:5] + str(new_id_num)
        elif int(new_id_num/100) == 0 and int(new_id_num/10) != 0: # if the new id number is in tens
            new_id = max(group_hid_list)[:5] + '0' + str(new_id_num)
        else:
            new_id = max(group_hid_list)[:5] + '00' + str(new_id_num)
        
        return new_id
    
    
    
    
    def assign_new_pid(self, pp):
        '''
        Assign a PID for a newly created person pp
        '''
        
        temp_pid_list = list()

        # Find the PIDs in this household that begin with its HID
        for PID in self.hh_dict[pp.HID].own_pp_dict: 
            if PID[:-2] == pp.HID:
                temp_pid_list.append(PID)

        if len(temp_pid_list) != 0:
            temp_pid = max(temp_pid_list)
            new_id_num = int(temp_pid[-2:]) + 1
            
            if int(new_id_num/10) != 0: # if the new id number is in tens
                new_id = pp.HID + str(new_id_num)
            else:
                new_id = pp.HID + '0' + str(new_id_num)
        
        else:
            new_id = pp.HID + '01' # First member in the household with a PID that begins with its own HID
        
        return new_id
    
    
    

    def assign_gender(self):
        '''
        Random assign a gender to a newly created Person
        '''
        return int(round(random.random(), 0))
    
    
        
    

    def get_siblings(self, pp):
        '''
        Find all siblings of a person pp; returned in a list of person instances
        '''
    
        sibling_list = list()
        
        if pp.FatherID == 0 and pp.MotherID == 0: # Then find siblings within the household by R2HHH
            
            for HID in self.hh_dict:
                if self.hh_dict[HID].is_exist == 1:
                    if HID == pp.HID:
                        for PID in self.hh_dict[HID].own_pp_dict:
                            sb = self.hh_dict[HID].own_pp_dict[PID]
                            if sb.is_alive == 1:
                            
                                if pp.R2HHH == '3_00_1': # pp is household head
        
                                    if sb.R2HHH == '3_01_1' or sb.R2HHH == '3_02_1' or sb.R2HHH == '3_03_1' or sb.R2HHH == '3_04_1' or sb.R2HHH == '3_05_1':
                                        sibling_list.append(sb)
                                        
                                elif pp.R2HHH == '4_00_1' or pp.R2HHH == '4_01_1' or pp.R2HHH == '4_02_1' or pp.R2HHH == '4_03_1' or pp.R2HHH == '4_04_1' or pp.R2HHH == '4_05_1' or pp.R2HHH == '4_06_1' or pp.R2HHH == '4_07_1' or pp.R2HHH == '4_08_1' or pp.R2HHH == '4_09_1':
                                # pp is in the 4th generation
                                    if sb.R2HHH == '4_00_1' or sb.R2HHH == '4_01_1' or sb.R2HHH == '4_02_1' or sb.R2HHH == '4_03_1' or sb.R2HHH == '4_04_1' or sb.R2HHH == '4_05_1' or sb.R2HHH == '4_06_1' or sb.R2HHH == '4_07_1' or sb.R2HHH == '4_08_1' or sb.R2HHH == '4_09_1':
                                        if pp.PID != sb.PID:
                                            sibling_list.append(sb)
                                
                                elif pp.R2HHH == '5_00_1' or pp.R2HHH == '5_01_1' or pp.R2HHH == '5_02_1' or pp.R2HHH =='5_03_1':
                                # pp is in the 5th generation
                                    if sb.R2HHH == '5_00_1' or sb.R2HHH == '5_01_1' or sb.R2HHH == '5_02_1' or sb.R2HHH =='5_03_1':
                                        if pp.PID != sb.PID:
                                            sibling_list.append(sb)
        
        else:
            if pp.FatherID == 0: # Then find siblings by mother ID
                
                for HID in self.hh_dict:
                    if self.hh_dict[HID].is_exist == 1:
                        for PID in self.hh_dict[HID].own_pp_dict:
                            sb = self.hh_dict[HID].own_pp_dict[PID]
                            if sb.is_alive == 1:
                            
                                if sb.MotherID == pp.MotherID:
                                    sibling_list.append(sb)
            
            else: # Then find siblings by father ID
                
                for HID in self.hh_dict:
                    if self.hh_dict[HID].is_exist == 1:                    
                        for PID in self.hh_dict[HID].own_pp_dict:
                            sb = self.hh_dict[HID].own_pp_dict[PID]
                            if sb.is_alive == 1:
                            
                                if sb.FatherID == pp.FatherID:
                                    sibling_list.append(sb)
                
        return sibling_list
    

    def get_father(self, pp):
        '''
        Find father of pp.
        '''
        
        for HID in self.hh_dict:
            if self.hh_dict[HID].is_exist == 1:            
                for PID in self.hh_dict[HID].own_pp_dict:
                    ff = self.hh_dict[HID].own_pp_dict[PID]
                        
                    if ff.PID == pp.FatherID and ff.is_alive == 1:
                        return ff
        
#         # The following codes are for the occasion when pp.FatherID does not exist;
#         # This is a problem related to the imperfectness of the original Wolong DB;
#         # And they seem not influence the program's performance if totally removed.
#
#         if pp.FatherID == 0: # Then find father within the household by R2HHH     
#             
#             for HID in self.cur_hh_dict:
#                 if HID == pp.HID:
#                     for PID in self.cur_hh_dict[HID].cur_own_pp_dict:
#                         ff = self.cur_hh_dict[HID].cur_own_pp_dict[PID]
#                         
#                         if pp.R2HHH == '2_00_1':
#                             if ff.PID == '1_00_1':
#                                 return ff
#                         
#                         if pp.R2HHH == '3_00_1' or pp.R2HHH == '3_01_1' or pp.R2HHH == '3_02_1' or pp.R2HHH == '3_03_1' or pp.R2HHH == '3_04_1' or pp.R2HHH == '3_05_1':
#                             if ff.PID == '2_00_1':
#                                 return ff
#                         
#                         if pp.R2HHH == '4_00_1' or pp.R2HHH == '4_01_1' or pp.R2HHH == '4_02_1' or pp.R2HHH == '4_03_1' or pp.R2HHH == '4_04_1' or pp.R2HHH == '4_05_1' or pp.R2HHH == '4_06_1' or pp.R2HHH == '4_07_1' or pp.R2HHH == '4_08_1' or pp.R2HHH == '4_09_1':
#                             if ff.PID == '3_00_1':
#                                 return ff
#                         
#                         if pp.R2HHH == '5_00_1' or pp.R2HHH == '5_01_1' or pp.R2HHH == '5_02_1' or pp.R2HHH =='5_03_1':
#                             if ff.PID == '4_00_1': # Need elaboration
#                                 return ff

                

    def get_mother(self, pp):
        '''
        Find mother of pp.
        '''
        
        for HID in self.hh_dict:
            if self.hh_dict[HID].is_exist == 1:                 
                for PID in self.hh_dict[HID].own_pp_dict:
                    mm = self.hh_dict[HID].own_pp_dict[PID]
                        
                    if mm.PID == pp.MotherID and mm.is_alive == 1:
                        return mm
        


    def get_children(self, pp):
        '''
        Find all children of a person pp; returned in a list of person instances        
        '''
        
        # Define returned list
        kid_list = list()
        
        for HID in self.hh_dict:
            if self.hh_dict[HID].is_exist == 1:                 
                for PID in self.hh_dict[HID].own_pp_dict:
                    kid = self.hh_dict[HID].own_pp_dict[PID]
                    if kid.is_alive == 1:
                    
                        if pp.Gender == 1: # Male
                            if kid.FatherID == pp.PID:
                                kid_list.append(kid)
                        else: # Female
                            if kid.MotherID == pp.PID:
                                kid_list.append(kid)
        
        return kid_list

    



    def get_relation_to_hh_head(self, pp, role):
        '''
        The whole concept of household head is of no more relevance in this Python version of SEEMS.
        I keep this submodule just for future references.

        This submodule needs elaboration to fulfill its original designed functions.
        
        # "Role" indicates as what role the person, pp, is added to the household (thus needs getting the relationship to the household head;
        # There are only two possible roles, child or spouse;
        # If child, the only possible relationships are sons(daughters), grandsons(grand-daughters), grand-grand children, etc;
        # If spouse, the only possible relationships are wives, daughters-in-law, grand-daughters-in-law, etc
        '''
        
        relation = ''
        
#         if role == 'child':
#             if self.get_father(pp).R2HHH == '3_00_1':
#                 relation = '4' # Need elaborate
#                 
#             elif self.get_father(pp).R2HHH == '4_00_1': # Need elaborate
#                 relation = '5'
#         
#         else: # spouse
#             if self.cur_hh_dict[pp.HID].cur_own_pp_dict[pp.SpouseID].R2HHH == '3_00_1':
#                 relation = '3_00_0'
#             
#             elif self.cur_hh_dict[pp.HID].cur_own_pp_dict[pp.SpouseID].R2HHH == '4_00_1': # Need elaborate
#                 relation = '4_00_0'
#                 
#             elif self.cur_hh_dict[pp.HID].cur_own_pp_dict[pp.SpouseID].R2HHH == '5_00_1': # Need elaborate
#                 relation = '5_00_0'
                    
        return relation
    



    
    
    
    