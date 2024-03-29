

__all__ = ['crossval_table']

from Gaugi.tex import *
from Gaugi.messenger.macros import *
from Gaugi import Logger, expandFolders, load
from functools import reduce

import matplotlib as mpl
import matplotlib.pyplot as plt
import collections, os, glob, json, copy, re
import numpy as np
import pandas as pd
import os
import json
import tensorflow as tf
model_from_json = tf.keras.models.model_from_json




class crossval_table( Logger ):

    #
    # Constructor
    #
    def __init__(self, config_dict, etbins=None, etabins=None ):

        Logger.__init__(self)
        self.__table = None
        # Check wanted key type
        self.__config_dict = collections.OrderedDict(config_dict) if type(config_dict) is dict else config_dict
        self.__etbins = etbins
        self.__etabins = etabins


    #
    # Fill the main dataframe with values from the tuning files and convert to pandas dataframe
    #
    def fill(self, path, tag):

        paths = expandFolders( path )
        MSG_INFO(self, "Reading file for %s tag from %s", tag , path)

        # Creating the dataframe
        dataframe = collections.OrderedDict({
                              'train_tag'      : [],
                              'et_bin'         : [],
                              'eta_bin'        : [],
                              'model_idx'      : [],
                              'sort'           : [],
                              'init'           : [],
                              'file_name'      : [],
                              'tuned_idx'      : [],
                          })


        # Complete the dataframe for each varname in the config dict
        for varname in self.__config_dict.keys():
            dataframe[varname] = []

        MSG_INFO(self, 'There are %i files for this task...' %(len(paths)))
        MSG_INFO(self, 'Filling the table... ')

        for ituned_file_name in paths:
            gfile = load(ituned_file_name)
            tuned_file = gfile['tunedData']

            for idx, ituned in enumerate(tuned_file):
                history = ituned['history']
                #model = model_from_json( json.dumps(ituned['sequence'], separators=(',', ':')) , custom_objects={'RpLayer':RpLayer} )
                #model.set_weights( ituned['weights'] )

                # get the basic from model
                dataframe['train_tag'].append(tag)
                #dataframe['model'].append(model)
                dataframe['model_idx'].append(ituned['imodel'])
                dataframe['sort'].append(ituned['sort'])
                dataframe['init'].append(ituned['init'])
                dataframe['et_bin'].append(self.get_etbin(ituned_file_name))
                dataframe['eta_bin'].append(self.get_etabin(ituned_file_name))
                dataframe['file_name'].append(ituned_file_name)
                dataframe['tuned_idx'].append( idx )

                # Get the value for each wanted key passed by the user in the contructor args.
                for key, local  in self.__config_dict.items():
                    dataframe[key].append( self.__get_value( history, local ) )


        self.__table = self.__table.append( pd.DataFrame(dataframe) ) if not self.__table is None else pd.DataFrame(dataframe)
        MSG_INFO(self, 'End of fill step, a pandas DataFrame was created...')


    #
    # Convert the table to csv
    #
    def to_csv( self, output ):
        self.__table.to_csv(output)


    #
    # Read the table from csv
    #
    def from_csv( self, input ):
        self.__table = pd.read_csv(input)


    #
    # Get the main table
    #
    def table(self):
        return self.__table


    #
    # Set the main table
    #
    def set_table(self, table):
        self.__table=table


    #
    # Get the value using recursive dictionary navigation
    #
    def __get_value(self, history, local):

        # Protection to not override the history since this is a 'mutable' object
        var = copy.copy(history)
        for key in local.split('/'):
            var = var[key.split('#')[0]][int(key.split('#')[1])] if '#' in key else var[key]
        return var


    def get_etbin(self, job):
        return int(  re.findall(r'et[a]?[0-9]', job)[0][-1] )


    def get_etabin(self, job):
        return int( re.findall(r'et[a]?[0-9]',job)[1] [-1] )


    def get_etbin_edges(self, et_bin):
        return (self.__etbins[et_bin], self.__etbins[et_bin+1])


    def get_etabin_edges(self, eta_bin):
        return (self.__etabins[eta_bin], self.__etabins[eta_bin+1])


    #
    # Get the pandas dataframe
    #
    def table(self):
        return self.__table


    #
    # Return only best inits
    #
    def filter_inits(self, key):
        return self.table().loc[self.table().groupby(['et_bin', 'eta_bin', 'model_idx', 'sort'])[key].idxmax(), :]


    #
    # Get the best sorts from best inits table
    #
    def filter_sorts(self, best_inits, key):
        return best_inits.loc[best_inits.groupby(['et_bin', 'eta_bin', 'model_idx'])[key].idxmax(), :]


    #
    # Calculate the mean/std table from best inits table
    #
    def describe(self, best_inits ):

        # Create a new dataframe to hold this table
        dataframe = { 'train_tag' : [], 'et_bin' : [], 'eta_bin' : []}
        # Include all wanted keys into the dataframe
        for key in self.__config_dict.keys():
            if 'passed' in key: # Skip counts
                continue
            elif ('op' in key) or ('val' in key):
                dataframe[key+'_mean'] = []; dataframe[key+'_std'] = [];
            else:
                dataframe[key] = []

        # Loop over all tuning tags and et/eta bins
        for tag in best_inits.train_tag.unique():
            for et_bin in best_inits.et_bin.unique():
                for eta_bin in best_inits.eta_bin.unique():

                  cv_bin = best_inits.loc[ (best_inits.train_tag == tag) & (best_inits.et_bin == et_bin) & (best_inits.eta_bin == eta_bin) ]
                  dataframe['train_tag'].append( tag ); dataframe['et_bin'].append( et_bin ); dataframe['eta_bin'].append( eta_bin )
                  for key in self.__config_dict.keys():
                      if 'passed' in key:
                        continue
                      elif ('op' in key) or ('val' in key):
                          dataframe[key+'_mean'].append( cv_bin[key].mean() ); dataframe[key+'_std'].append( cv_bin[key].std() )
                      else:
                          dataframe[key].append( cv_bin[key].unique()[0] )

        # Return the pandas dataframe
        return pd.DataFrame(dataframe)



    #
    # Get tge cross val integrated table from best inits
    #
    def integrate( self, best_inits, tag ):

        keys = [ key for key in self.__config_dict.keys() if 'passed' in key or 'total' in key]
        table = best_inits.loc[best_inits.train_tag==tag].groupby(['sort']).agg(dict(zip( keys, ['sum']*len(keys))))
        for key in keys:
            if 'passed' in key:
                orig_key = key.replace('_passed','')
                values = table[key].div( table[orig_key+'_total'] )
                table[orig_key] = values
                table=table.drop([key],axis=1)
                table=table.drop([orig_key+'_total'],axis=1)

        return table.agg(['mean','std'])



    #
    # Dump all history for each line in the table
    #
    def dump_all_history( self, table, output_path , tag):
        if not os.path.exists( output_path ):
          os.mkdir( output_path )
        for _ , row in table.iterrows():
            if row.train_tag != tag:
              continue
            # Load history
            history = load( row.file_name )['tunedData'][row.tuned_idx]['history']
            history['loc'] = {'et_bin' : row.et_bin, 'eta_bin' : row.eta_bin, 'sort' : row.sort, 'model_idx' : row.model_idx}
            name = 'history_et_%i_eta_%i_model_%i_sort_%i.json' % (row.et_bin,row.eta_bin,row.model_idx,row.sort)
            with open(os.path.join(output_path, '%s' %name), 'w') as fp:
                #json.dump(transform_serialize(history), fp)
                json.dump(str(history), fp)



    def get_model( self, path, index ):
      tuned_list = load(path)['tunedData']
      for tuned in tuned_list:
        if tuned['imodel'] == index:
          return tuned
      MSG_FATAL( self, "It's not possible to find the history for model index %d", index )



		#
		# Plot the training curves for all sorts.
		#
    def plot_training_curves( self, best_inits, best_sorts, dirname, display=False, start_epoch=3 ):

        basepath = os.getcwd()
        if not os.path.exists(basepath+'/'+dirname):
          os.mkdir(basepath+'/'+dirname)

        def plot_training_curves_for_each_sort(table, et_bin, eta_bin, best_sort , output, display=False, start_epoch=0):
            table = table.loc[(table.et_bin==et_bin) & (table.eta_bin==eta_bin)]
            nsorts = len(table.sort.unique())
            fig, ax = plt.subplots(nsorts,2, figsize=(15,20))
            fig.suptitle(r'Monitoring Train Plot - Et = %d, Eta = %d'%(et_bin,eta_bin), fontsize=15)
            for idx, sort in enumerate(table.sort.unique()):
                current_table = table.loc[table.sort==sort]
                path=current_table.file_name.values[0]
                history = self.get_model( path, current_table.model_idx.values[0])['history']

                best_epoch = history['max_sp_best_epoch_val'][-1] - start_epoch
                # Make the plot here
                ax[idx, 0].set_xlabel('Epochs')
                ax[idx, 0].set_ylabel('Loss (sort = %d)'%sort, color = 'r' if best_sort==sort else 'k')
                ax[idx, 0].plot(history['loss'][start_epoch::], c='b', label='Train Step')
                ax[idx, 0].plot(history['val_loss'][start_epoch::], c='r', label='Validation Step')
                ax[idx, 0].axvline(x=best_epoch, c='k', label='Best epoch')
                ax[idx, 0].legend()
                ax[idx, 0].grid()
                ax[idx, 1].set_xlabel('Epochs')
                ax[idx, 1].set_ylabel('SP (sort = %d)'%sort, color = 'r' if best_sort==sort else 'k')
                ax[idx, 1].plot(history['max_sp_val'][start_epoch::], c='r', label='Validation Step')
                ax[idx, 1].axvline(x=best_epoch, c='k', label='Best epoch')
                ax[idx, 1].legend()
                ax[idx, 1].grid()

            plt.savefig(output)
            if display:
                plt.show()
            else:
                plt.close(fig)

        tag = best_inits.train_tag.unique()[0]
        for et_bin in best_inits.et_bin.unique():
            for eta_bin in best_inits.eta_bin.unique():
                best_sort = best_sorts.loc[(best_sorts.et_bin==et_bin) & (best_sorts.eta_bin==eta_bin)].sort
                plot_training_curves_for_each_sort(best_inits, et_bin, eta_bin, best_sort.values[0],
                    basepath+'/'+dirname+'/train_evolution_et%d_eta%d_%s.pdf'%(et_bin,eta_bin,tag), display, start_epoch)



		#
		# Plot the training curves for all sorts.
		#
    def plot_roc_curves( self, best_sorts, tags, legends, output, display=False, colors=None, points=None, et_bin=None, eta_bin=None,
                         xmin=-0.02, xmax=0.3, ymin=0.8, ymax=1.02, fontsize=18, figsize=(15,15)):


        def plot_roc_curves_for_each_bin(ax, table, colors, xmin=-0.02, xmax=0.3, ymin=0.8, ymax=1.02, fontsize=18):

          ax.set_xlabel('Fake Probability [%]',fontsize=fontsize)
          ax.set_ylabel('Detection Probability [%]',fontsize=fontsize)
          ax.set_title(r'Roc curve (et = %d, eta = %d)'%(table.et_bin.values[0], table.eta_bin.values[0]),fontsize=fontsize)

          for idx, tag in enumerate(tags):
              current_table = table.loc[(table.train_tag==tag)]

              path=current_table.file_name.values[0]
              history = self.get_model( path, current_table.model_idx.values[0])['history']
              pd, fa = history['summary']['rocs']['roc_op']
              ax.plot( fa, pd, color=colors[idx], linewidth=2, label=tag)
              ax.set_ylim(ymin,ymax)
              ax.set_xlim(xmin,xmax)

          ax.legend(fontsize=fontsize)
          ax.grid()


        if et_bin!=None and eta_bin!=None:
            fig, ax = plt.subplots(1,1, figsize=figsize)
            fig.suptitle(r'Operation ROCs', fontsize=15)
            table_for_this_bin = best_sorts.loc[(best_sorts.et_bin==et_bin) & (best_sorts.eta_bin==eta_bin)]
            plot_roc_curves_for_each_bin( ax, table_for_this_bin, colors, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, fontsize=fontsize)
            plt.savefig(output)
            if display:
                plt.show()
            else:
                plt.close(fig)

        else:

            n_et_bins = len(best_sorts.et_bin.unique())
            n_eta_bins = len(best_sorts.eta_bin.unique())
            fig, ax = plt.subplots(n_et_bins,n_eta_bins, figsize=figsize)
            fig.suptitle(r'Operation ROCs', fontsize=15)

            for et_bin in best_sorts.et_bin.unique():
                for eta_bin in best_sorts.eta_bin.unique():
                    table_for_this_bin = best_sorts.loc[(best_sorts.et_bin==et_bin) & (best_sorts.eta_bin==eta_bin)]
                    plot_roc_curves_for_each_bin( ax[et_bin][eta_bin], table_for_this_bin, colors, xmin=xmin, xmax=xmax,
                                                  ymin=ymin, ymax=ymax, fontsize=fontsize)

            plt.savefig(output)
            if display:
                plt.show()
            else:
                plt.close(fig)




    #
    # Create the beamer table file
    #
    def dump_beamer_table( self, best_inits, operation_points, output, tags=None, title='' ):

        cv_table = self.describe( best_inits )
        # Create Latex Et bins
        etbins_str = []; etabins_str = []
        for etBinIdx in range(len(self.__etbins)-1):
            etbin = (self.__etbins[etBinIdx], self.__etbins[etBinIdx+1])
            if etbin[1] > 100 :
                etbins_str.append( r'$E_{T}\text{[GeV]} > %d$' % etbin[0])
            else:
                etbins_str.append(  r'$%d < E_{T} \text{[Gev]}<%d$'%etbin )

        # Create Latex eta bins
        for etaBinIdx in range( len(self.__etabins)-1 ):
            etabin = (self.__etabins[etaBinIdx], self.__etabins[etaBinIdx+1])
            etabins_str.append( r'$%.2f<\eta<%.2f$'%etabin )

        # Default colors
        colorPD = '\\cellcolor[HTML]{9AFF99}'; colorPF = ''; colorSP = ''

        train_tags = cv_table.train_tag.unique() if not tags else tags

        # Apply beamer
        with BeamerTexReportTemplate1( theme = 'Berlin'
                                 , _toPDF = True
                                 , title = title
                                 , outputFile = output
                                 , font = 'structurebold' ):

            for operation_point in operation_points:
                ### Prepare tables
                tuning_names = ['']; tuning_names.extend( train_tags )
                lines1 = []
                lines1 += [ HLine(_contextManaged = False) ]
                lines1 += [ HLine(_contextManaged = False) ]
                lines1 += [ TableLine( columns = ['','','kinematic region'] + reduce(lambda x,y: x+y,[['',s,''] for s in etbins_str]), _contextManaged = False ) ]
                lines1 += [ HLine(_contextManaged = False) ]
                lines1 += [ TableLine( columns = ['Det. Region','Method','Type'] + reduce(lambda x,y: x+y,[[colorPD+r'$P_{D}[\%]$',colorSP+r'$SP[\%]$',colorPF+r'$P_{F}[\%]$'] \
                                      for _ in etbins_str]), _contextManaged = False ) ]
                lines1 += [ HLine(_contextManaged = False) ]

                for etaBinIdx in range(len(self.__etabins) - 1):
                    for idx, tag in enumerate( train_tags ):
                        cv_values=[]; ref_values=[]
                        for etBinIdx in range(len(self.__etbins) - 1):
                            current_table = cv_table.loc[ (cv_table.train_tag==tag) & (cv_table.et_bin==etBinIdx) & (cv_table.eta_bin==etaBinIdx) ]
                            sp = current_table[operation_point+'_sp_val_mean'].values[0]*100
                            pd = current_table[operation_point+'_pd_val_mean'].values[0]*100
                            fa = current_table[operation_point+'_fa_val_mean'].values[0]*100
                            sp_std = current_table[operation_point+'_fa_val_std'].values[0]*100
                            pd_std = current_table[operation_point+'_fa_val_std'].values[0]*100
                            fa_std = current_table[operation_point+'_fa_val_std'].values[0]*100
                            sp_ref = current_table[operation_point+'_sp_ref'].values[0]*100
                            pd_ref = current_table[operation_point+'_pd_ref'].values[0]*100
                            fa_ref = current_table[operation_point+'_fa_ref'].values[0]*100
                            cv_values   += [ colorPD+('%1.2f$\pm$%1.2f')%(pd,pd_std),colorSP+('%1.2f$\pm$%1.2f')%(sp,sp_std),colorPF+('%1.2f$\pm$%1.2f')%(fa,fa_std),    ]
                            ref_values  += [ colorPD+('%1.2f')%(pd_ref), colorSP+('%1.2f')%(sp_ref), colorPF+('%1.2f')%(fa_ref)]
                        if idx > 0:
                            lines1 += [ TableLine( columns = ['', tuning_names[idx+1], 'Cross Validation'] + cv_values   , _contextManaged = False ) ]
                        else:
                            lines1 += [ TableLine( columns = ['\multirow{%d}{*}{'%(len(tuning_names))+etabins_str[etaBinIdx]+'}',tuning_names[idx], 'Reference'] + ref_values   ,
                                                _contextManaged = False ) ]
                            lines1 += [ TableLine( columns = ['', tuning_names[idx+1], 'Cross Validation'] + cv_values    , _contextManaged = False ) ]

                    lines1 += [ HLine(_contextManaged = False) ]
                lines1 += [ HLine(_contextManaged = False) ]


                ### Calculate the final efficiencies
                lines2 = []
                lines2 += [ HLine(_contextManaged = False) ]
                lines2 += [ HLine(_contextManaged = False) ]
                lines2 += [ TableLine( columns = ['',colorPD+r'$P_{D}[\%]$',colorPF+r'$F_{a}[\%]$'], _contextManaged = False ) ]
                lines2 += [ HLine(_contextManaged = False) ]
                for idx, tag in enumerate( train_tags ):
                    current_table = self.integrate( best_inits, tag )
                    pd = current_table[operation_point+'_pd_op'].values[0]*100
                    pd_std = current_table[operation_point+'_pd_op'].values[1]*100
                    fa = current_table[operation_point+'_fa_op'].values[0]*100
                    fa_std = current_table[operation_point+'_fa_op'].values[1]*100
                    pd_ref = current_table[operation_point+'_pd_ref'].values[0]*100
                    fa_ref = current_table[operation_point+'_fa_ref'].values[0]*100
                    if idx > 0:
                        lines2 += [ TableLine( columns = [tag.replace('_','\_') ,
                          colorPD+('%1.2f$\pm$%1.2f')%(pd,pd_std),colorPF+('%1.2f$\pm$%1.2f')%(fa,fa_std) ], _contextManaged = False ) ]
                    else:
                      lines2 += [ TableLine( columns = ['Ref.' ,colorPD+('%1.2f')%(pd_ref),colorPF+('%1.2f')%(fa_ref) ], _contextManaged = False ) ]
                      lines2 += [ TableLine( columns = [tag.replace('_','\_') ,
                        colorPD+('%1.2f$\pm$%1.2f')%(pd,pd_std),colorPF+('%1.2f$\pm$%1.2f')%(fa,fa_std) ], _contextManaged = False ) ]


                # Create all tables into the PDF Latex
                with BeamerSlide( title = "The Cross Validation Efficiency Values For All Tunings"  ):
                    with Table( caption = 'The $P_{d}$, $F_{a}$ and $SP $ values for each phase space for each method.') as table:
                        with ResizeBox( size = 1. ) as rb:
                            with Tabular( columns = '|lcc|' + 'ccc|' * len(etbins_str) ) as tabular:
                                tabular = tabular
                                for line in lines1:
                                    if isinstance(line, TableLine):
                                        tabular += line
                                    else:
                                        TableLine(line, rounding = None)

                with BeamerSlide( title = "The General Efficiency"  ):
                    with Table( caption = 'The general efficiency for the cross validation method for each method.') as table:
                        with ResizeBox( size = 0.7 ) as rb:
                            with Tabular( columns = 'lc' + 'c' * 2 ) as tabular:
                                tabular = tabular
                                for line in lines2:
                                    if isinstance(line, TableLine):
                                        tabular += line
                                    else:
                                        TableLine(line, rounding = None)






    #
    # Load all keras models given the best sort table
    #
    def get_best_models( self, best_sorts , remove_last=True, with_history=False):

        from tensorflow.keras.models import Model, model_from_json
        import json

        models = [[ None for _ in range(len(self.__etabins)-1)] for __ in range(len(self.__etbins)-1)]
        for et_bin in range(len(self.__etbins)-1):
            for eta_bin in range(len(self.__etabins)-1):
                d_tuned = {}
                best = best_sorts.loc[(best_sorts.et_bin==et_bin) & (best_sorts.eta_bin==eta_bin)]
                tuned = load(best.file_name.values[0])['tunedData'][best.model_idx.values[0]]
                model = model_from_json( json.dumps(tuned['sequence'], separators=(',', ':')) ) #custom_objects={'RpLayer':RpLayer} )
                model.set_weights( tuned['weights'] )
                new_model = Model(model.inputs, model.layers[-2].output) if remove_last else model
                #new_model.summary()
                d_tuned['model']    = new_model
                d_tuned['etBin']    = [self.__etbins[et_bin], self.__etbins[et_bin+1]]
                d_tuned['etaBin']   = [self.__etabins[eta_bin], self.__etabins[eta_bin+1]]
                d_tuned['etBinIdx'] = et_bin
                d_tuned['etaBinIdx']= eta_bin
                d_tuned['history']  = tuned['history']
                models[et_bin][eta_bin] = d_tuned
        return models







if __name__ == "__main__":


    #
    # My local test to debug the cross validation table class
    #

    def create_op_dict(op):
        d = {
                  op+'_pd_ref'    : "reference/"+op+"_cutbased/pd_ref#0",
                  op+'_fa_ref'    : "reference/"+op+"_cutbased/fa_ref#0",
                  op+'_sp_ref'    : "reference/"+op+"_cutbased/sp_ref",
                  op+'_pd_val'    : "reference/"+op+"_cutbased/pd_val#0",
                  op+'_fa_val'    : "reference/"+op+"_cutbased/fa_val#0",
                  op+'_sp_val'    : "reference/"+op+"_cutbased/sp_val",
                  op+'_pd_op'     : "reference/"+op+"_cutbased/pd_op#0",
                  op+'_fa_op'     : "reference/"+op+"_cutbased/fa_op#0",
                  op+'_sp_op'     : "reference/"+op+"_cutbased/sp_op",

                  # Counts
                  op+'_pd_ref_passed'    : "reference/"+op+"_cutbased/pd_ref#1",
                  op+'_fa_ref_passed'    : "reference/"+op+"_cutbased/fa_ref#1",
                  op+'_pd_ref_total'     : "reference/"+op+"_cutbased/pd_ref#2",
                  op+'_fa_ref_total'     : "reference/"+op+"_cutbased/fa_ref#2",
                  op+'_pd_val_passed'    : "reference/"+op+"_cutbased/pd_val#1",
                  op+'_fa_val_passed'    : "reference/"+op+"_cutbased/fa_val#1",
                  op+'_pd_val_total'     : "reference/"+op+"_cutbased/pd_val#2",
                  op+'_fa_val_total'     : "reference/"+op+"_cutbased/fa_val#2",
                  op+'_pd_op_passed'     : "reference/"+op+"_cutbased/pd_op#1",
                  op+'_fa_op_passed'     : "reference/"+op+"_cutbased/fa_op#1",
                  op+'_pd_op_total'      : "reference/"+op+"_cutbased/pd_op#2",
                  op+'_fa_op_total'      : "reference/"+op+"_cutbased/fa_op#2",
        }
        return d


    tuned_info = collections.OrderedDict( {
                  # validation
                  "max_sp_val"      : 'summary/max_sp_val',
                  "max_sp_pd_val"   : 'summary/max_sp_pd_val#0',
                  "max_sp_fa_val"   : 'summary/max_sp_fa_val#0',
                  # Operation
                  "max_sp_op"       : 'summary/max_sp_op',
                  "max_sp_pd_op"    : 'summary/max_sp_pd_op#0',
                  "max_sp_fa_op"    : 'summary/max_sp_fa_op#0',
                  #"loss"            : 'loss',
                  #"val_loss"        : 'val_loss',
                  #"accuracy"        : 'accuracy',
                  #"val_accuracy"    : 'val_accuracy',
                  #"max_sp_best_epoch_val": 'max_sp_best_epoch_val',
                  } )

    tuned_info.update(create_op_dict('tight'))
    tuned_info.update(create_op_dict('medium'))
    tuned_info.update(create_op_dict('loose'))
    tuned_info.update(create_op_dict('vloose'))


    etbins = [15,20,30,40,50,100000]
    etabins = [0, 0.8 , 1.37, 1.54, 2.37, 2.5]

    cv  = crossval_table( tuned_info, etbins = etbins , etabins = etabins )

    #cv.fill( '/Volumes/castor/tuning_data/Zee/v10/*.r2/*/*.gz', 'v10')
    #cv.to_csv( 'v10.csv' )
    cv.from_csv( 'v10.csv' )
    best_inits = cv.filter_inits("max_sp_val")
    best_inits = best_inits.loc[(best_inits.model_idx==0)]
    best_sorts = cv.filter_sorts(best_inits, 'max_sp_val')

    print(best_inits.head())
    cv.dump_beamer_table( best_inits, ['vloose'], 'test', tags=['v10'], title='' )
    #cv.plot_training_curves( best_inits, best_sorts, 'v11' )


