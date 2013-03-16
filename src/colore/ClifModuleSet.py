'''
Created on 2010-11-05
Regrouped all methods that pertain to an import hierarchy into the new module ClifModuleSet on 2013-03-15

@author: Torsten Hahmann
'''

import sys
from ClifModule import ClifModule
import atexit, os, datetime, filemgt, process, commands


class ClifModelSet(object):

    imports = []
    nonlogical_symbols = []
    primitive_predicates = []
    defined_predicates = []
    nonskolem_functions = []
    replaceable_symbols = []
    
    translations = {}
    

    # initialize with a set of files to be processed (for lemmas)
    def __init__(self, processing=None):

        self.p9_file_name = ''
        self.tptp_file_name = ''

        # list of clif files still to process
        self.processing = []
        # list of already processes clif imports (list of ClifModule)
        self.imports = []
        # list of nonlogical symbols that occur in any imported files
        # it is a tuple [symbol, count, d_min, d_max] where
        # symbol: name of the symbol
        # count: total number of Occurrences
        # d_min: minimal depth in the CL-import tree where it occurs
        # d_max: maximal depth in the CL-import tree where it occurs
        self.nonlogical_symbols = []
        # the primitive and potentially some defined predicates occurring in any imported files
        self.primitive_predicates = []
        # a list of predicates that are definitively defined predicates occurring in any imported files
        self.defined_predicates = []
        # the functions occurring in any imported files
        self.nonskolem_functions = []
        # list of special symbols that will be replaced in the p9 and the tptp translation
        self.replaceable_symbols = []

        if processing:
            self.processing = processing
          
    def set_module_name(self,module_name):  
        """initially set the name of the top module
           NOT to be used later on"""
        self.processing.append((module_name, 0))

    def get_module_name(self):
        """return the name of the top module"""
        if len(self.imports)>0:
            return self.imports[0].module_name

    def update_nonlogical_symbols(self,new_nonlogical_symbols,depth):
        """update the ClifModuleSet's list of nonlogical symbols with the symbols in new_nonlogical_symbols
           new_nonlogical_symbols -- list of tuples (symbol_name, number of modules this occurs in, minimal_depth in import tree, maximal_depth in import tree)
         """
        for symbol in new_nonlogical_symbols:
            found = False
            for (entity, count, d_min, d_max) in self.nonlogical_symbols:
                if symbol == entity:
                    # already in named entities, we just update the count and the depth:
                    # we want to keep track of two kinds of depths: the minimal and the maximal
                    # the new max. depth is the furthest away from the actual module_name as possible
                    found = True
                    index = self.nonlogical_symbols.index([symbol, count, d_min, d_max])
                    self.nonlogical_symbols[index]=[symbol, count+1, d_min, depth]
                    break;
                else:
                    continue
            if not found:
                #print 'found ' + words[0] + ' in line: ' + line
                #a NEW meaningful named entity has been found
                self.nonlogical_symbols.append([symbol, 1, depth, depth])


    def prepare(self):
        """process the processing list until it is empty: create the list of imports (list of ClifModules)"""
        while self.processing:
            (module, depth) = self.processing[0]
            #print 'processing list:'
            #print self.processing
            m = ClifModule(self, module, depth)
            self.processing.remove((module, depth))
            self.imports.append(m)
            self.update_nonlogical_symbols(m.get_nonlogical_symbols(), m.get_depth())

        atexit.register(self.cleanup)
        
    
    def append_module(self,new_module_name, depth):
        """add a module to the processing list if it hasn't been included before"""
        existing = False
        # self.processing is a list of names
        for (p, _) in self.processing:
            if new_module_name == p:
                existing=True
                break
        # self.imports is a list of ClifModules
        for p in self.imports:
            if new_module_name == p.module_name:
                existing=True
                break 
        if not existing:
            print '|-- imports: ' + new_module_name + ' (depth ' + str(depth) + ')'
            # This is the only place where we increase the depth!!
            self.processing.append((new_module_name, depth))
    

    # extract the predicates and functions from prover9 mock run
    def extract_p9_predicates_and_functions (self):
    
        #print 'extract predicates and functions'
        prover9args = 'prover9 -t 0 -f '
        
    
        for f in self.imports:
            prover9args += f.p9_file_name + ' '
        
        options_file = commands.get_p9_optionsfile(self.get_module_name(), verbose=False)
        prover9args += ' ' + options_file + ' '

        
        # would be better to create a temporary file or read the output stream directly
        temp_file = self.get_module_name() + '_order' + filemgt.read_config('ladr','ending')
        prover9args += ' > ' + temp_file
        print prover9args
        process.createSubprocess(prover9args)
        p9.wait()
        
        order_file = open(temp_file, 'r')
        line = order_file.readline()
        predicates = None
        functions = None
        while line:
            if line.find('predicate_order') > -1:
                predicateline = line[line.find('predicate_order([')+len('predicate_order([')+1:-4]
                predicates = predicateline.split()
                for i in range(len(predicates)):
                    predicates[i] = predicates[i].replace(',','')
                line = order_file.readline()
                functionline = line[line.find('function_order([')+len('function_order([')+1:-4]
                functions = functionline.split()
                for i in range(len(functions)):
                    functions[i] = functions[i].replace(',','')
                break
            line = order_file.readline()
            
        order_file.close()
        #print 'temp file : ' + temp_file
        #print 'options file : ' + options_file
        os.remove(temp_file)
        os.remove(options_file)
        if predicates and functions:
            return (predicates, functions)
        else:
            return ([], [])

    # extracts the predicates and functions from the output of a prover9 mock run
    def get_predicates_and_functions (self):
      
        # process the predicates and functions
        predicates = []
        functions = [] 
    
        (predicates, functions) = self.extract_p9_predicates_and_functions()
        
        #print 'all predicates: ' + str(predicates)
        #print 'all functions: ' + str(functions)
        #print 'all named entities: ' + str(namedentities)
    
        # extracting defined predicates, (potentially) primitive predicates, and functions   
        for function in functions:
            for (entity, count, depth_min, depth_max) in self.nonlogical_symbols:
                if function == entity:
                    self.nonskolem_functions.append([entity, count, depth_min, depth_max])
    
        for (predicate, count, depth_min, depth_max) in self.nonlogical_symbols:
            if predicate in predicates:
                self.primitive_predicates.append([predicate, count, depth_min, depth_max])
            else:
                if predicate not in functions:
                    self.defined_predicates.append([predicate, count, depth_min, depth_max])
        
        print 'all primitive predicates: ' + str(self.primitive_predicates)
        print 'all defined predicates: ' + str(self.defined_predicates)
        print 'all functions: ' + str(self.nonskolem_functions)
    
    
    def select_systems (self, outfile_stem):
        """read the activated provers and model finders from the configuration file
        return values:
        provers_dict -- a dictionary of all provers to be used with commands as keys and a set of return values as value
        finders_dict -- a dictionary of all model finders to be used with commands as keys and a set of return values as value
        """
        provers_dict = {}
        finders_dict = {}
        
        provers = filemgt.read_config('active','provers').split(',')
        finders = filemgt.read_config('active','modelfinders').split(',')
        
        provers = [ s.strip() for s in provers ]
        finders = [ s.strip() for s in finders ]
        
        for prover in provers:
            codes = self.get_posititve_returncodes(prover)
            cmd = commands.get_system_command(prover, self.imports, outfile_stem)
            provers_dict[cmd] = codes
            self.provers[prover] = cmd
        for finder in finders:
            codes = self.get_posititve_returncodes(finder)
            cmd = commands.get_system_command(finder, self.imports, outfile_stem)
            finders_dict[cmd] = codes
            self.finders[finder] = cmd
        
        return (provers_dict, finders_dict)
            
    
    def get_posititve_returncodes(self,name):
        return self.get_returncodes(name)
    
    def get_unknown_returncodes(self,name):
        return self.get_returncodes(name, type="unknown_returncode")
        
    def get_returncodes(self,name,type="positive_returncode"):
        codes = filemgt.read_config(name,type).split(',')
        codes = [ int(s.strip()) for s in codes ]
        return codes
        
    
    def consolidate_results(self, provers_rc, finders_rc):
        """ check all the return codes from the provers and model finders to find whether a model or inconsistency has been found
        return values:
        consistent (-1) -- an inconsistency has been found in the ontology
        unknown (0) -- unknown result (no model and no inconsistency found)
        inconsistent (1) -- model found, the ontology is consistent
         """
        return_value = 0
         
        for finder in self.finders.keys():
            rc = finders_rc[self.finders[finder]]
            if rc in self.get_posititve_returncodes(finder):
                return_value = 1
            elif rc not in self.get_unknown_returncodes(finder):
                print finder + ' returned with unknown error code ' + str(rc)
        for prover in self.provers.keys():
            rc = provers_rc[self.provers[prover]]
            if rc in self.get_posititve_returncodes(prover):
                if not return_value==1:
                    return_value = -1
                else:
                    return_value == -100 
            elif rc not in self.get_unknown_returncodes(prover):
                print prover + ' returned with unknown error code ' + str(rc)
    
        if return_value==-1: return "inconsistent"
        elif return_value==1: return "consistent"
        elif return_value==0: return "unknown"
        else: return "contradiction"
    
        
    def run_consistency_check(self, options_files = None):
        """ test the input for consistency by trying to find a model or an inconsistency"""
        if self.run_prover:    
            # want to create a subfolder for the output files
            outfile_stem = filemgt.get_name_with_subfolder(self.imports[0].module_name, 
                                                            filemgt.read_config('output','folder')) 
            
            (provers, finders) = self.select_systems(outfile_stem)
            
            # run provers and modelfinders simultaneously and wait until one returns
            (prc, frc) = process.raceProcesses(provers, finders)

            print self.consolidate_results(provers, finders)
    
       
    # get a list of all p9files created here
    def get_p9_files(self):
        p9_files = []
        for m in self.imports:
            p9_files.append(m.p9_file_name)
        return p9_files
   

    # translate the module and all imported modules (Common Logic files) to a single TPTP file
    def get_single_tptp_file (self, number=0):
        
        single_p9_file = ladr.get_single_p9_file(get_module_name)
        ending = ''
        if not number==0:
            ending = '_' + str(number)

        self.tptp_file_name = filemgt.get_name_with_subfolder(self.imports[0].module_name,
                                                              filemgt.read_config('tptp','folder'),
                                                              ending + filemgt.read_config('tptp','all_ending'))
        
        TPTP.ladr_to_tptp(self.p9_file_name, self.tptp_file_name)      

    
#    def check_consistency(self):
#        (predicates_primitive, self.predicates_defined, self.functions_nonskolem) = self.get_predicates_and_functions(p9_files, namedentities)
#        if not self.test_heuristics:
#            # single run
#            #weights = PredicateWeightHeuristic.predicate_weight_heuristic_occurence_count(predicates_primitive, [])
#            #weights_file = PredicateWeightHeuristic.create_predicate_weight_file(imported[0][0] + '.weights', weights)
#            self.weights_file = None
#            if self.run_prover:
#                #run_consistency_checks(imported[0][0] + '_oc' , p9_files, [options_file, weights_file])
#                self.run_consistency_checks(self.imports[0], self.get_p9_files()) 
#        else:
#            # testing with multiple heuristics
#            orders = HeuristicTestSet.get_all_tests(self.imported[0][0], predicates_primitive, None)
#            if self.run_prover:
#                print ' ---- EXPERIMENTS ---- '
#                for order in orders:
#                    print '----------------------' 
#                    print '--- TESTCASE: ' + order[0] + ' ---' 
#                    print '----------------------' 
#                    self.run_consistency_checks(self.imported[0][0] + '_' + order[0], p9_files, [options_file, order[1]])


    # delete unnecessary files at the end
    def cleanup(self):
        if self.tidy:          
            LADR.cleanup_option_files()  
            for m in self.imports:
                if os.path.exists(m.p9_intermediary_file_name):
                    os.remove(m.p9_intermediary_file_name)
                if os.path.exists(m.clif_processed_file_name):
                    os.remove(m.clif_processed_file_name)
            