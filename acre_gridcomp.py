# =======================================================================================
##
# For usage: $python acre_gridcomp.py -h
#
#
#
# This script is intended to diagnose the output of gridded CLM/ELM/FATES
# simulations, for rapid visualization.
#
# Options include 1) the ability to do a regression against another set of files (base).
#                 3) plotting (most of the analysis right now is visual, not much
#                              really happens right now without plotting)
#
#  UNcomment the imported "code" library and add the following call
#  in the code where you want to add a debug stop:
#        code.interact(local=locals())
#
#
#
# =======================================================================================

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import sys
import getopt
import code  # For development: code.interact(local=locals())
import time
from scipy.io import netcdf
from mpl_toolkits.basemap import Basemap

# Some constants
g_to_Mg = 1.0e-6
m2_to_ha = 1.0e-4

ylgn_seq_cmap=mpl.cm.get_cmap('YlGn')
rdbu_div_cmap=mpl.cm.get_cmap('RdBu')

def usage():
     print('')
     print('=======================================================================')
     print('')
     print(' python acre_gridcomp.py -h --plotmode --regressmode')
     print('                         --test-hist-file=<path> --base-hist-file=<path>')
     print('                         --test-name=<text> --base-name=<text>')
     print('')
     print('  This script is intended to diagnose the output of one or two gridded')
     print('  runs, as a rapid pass/fail visual analysis of spatial ecosystem patterns')
     print('  that have emerged over time.')
     print('')
     print('')
     print(' -h --help ')
     print('     print this help message')
     print('')
     print(' --regressmode')
     print('     [Optional] logical switch, turns on regression tests')
     print('     against a baseline. Requires user to also set --base-rest-pref')
     print('     default is False')
     print('')
     print(' --eval-id=<id-string>')
     print('     a string that gives a name, or some id-tag associated with the')
     print('     evaluation being conducted. This will be used in output file naming.')
     print('     Any spaces detected in string will be trimmed.')
     print('')
     print(' --test-hist-file=<path>')
     print('     the full path to the history file of the test')
     print('     version of output')
     print('') 
     print(' --base-hist-file=<path>')
     print('     [Optional]  the full path to history file of a baseline')
     print('     version of output')
     print('') 
     print(' --test-name=<text>')
     print('     [Optional] a short descriptor for the test case that will be used')
     print('     for labeling plots. The default for the test case is "test".')
     print('')
     print(' --base-name=<text>')
     print('     [Optional] a short descriptor for the base case that will be used')
     print('     for labeling plots. The default for the base case is "base".')
     print('')
     print('')
     print('=======================================================================')


# ========================================================================================

## interp_args processes the arguments passed to the python script at executions.
#  The options are parsed and logical checks and comparisons are made.
# @param argv
# @return plotmode
# @return regressionmode
# @return restartmode
# @return test_r_prefix
# @return base_r_prefix
# @return test_h_prefix
# @return base_h_prefix
# @return test_name
# @return base_name

def interp_args(argv):

    argv.pop(0)  # The script itself is the first argument, forget it

    ## Binary flag that turns on and off regression tests against a baseline run
    regressionmode = False
    ## history file from the test simulation
    test_h_file = ''
    ## history file from the base simulation
    base_h_file = ''
    ## Name of the evaluation being performed, this is non-optional
    eval_id = ''
    ## Name for plot labeling of the test case
    test_name = 'test'
    ## Name for plot labeling of the base case
    base_name = 'base'

    try:
        opts, args = getopt.getopt(argv, 'h',["help","regressmode",     \
                                              "eval-id=",            \
                                              "test-hist-file=","base-hist-file=", \
                                              "test-name=","base-name="])

    except getopt.GetoptError as err:
        print('Argument error, see usage')
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(0)
        elif o in ("--regressmode"):
            regressionmode = True
        elif o in ("--eval-id"):
            eval_id = a
        elif o in ("--test-hist-file"):
            test_h_file = a
        elif o in ("--base-hist-file"):
            base_h_file = a
        elif o in ("--test-name"):
            test_name = a
        elif o in ("--base-name"):
            base_name = a
        else:
            assert False, "unhandled option"

    if(regressionmode):
        print('Regression Testing is ON')
        if(base_h_file==''):
            print('In a regression style comparison, you must specify a')
            print('path to baseline history files. See usage:')
            usage()
            sys.exit(2)
    else:
        print('Regression Testing is OFF')

    if(test_h_file==''):
        print('A path to history files is required input, see usage:')
        usage()
        sys.exit(2)

    if(eval_id==''):
        print('You must provide a name/id for this evaluation, see --eval-id:')
        usage()
        sys.exit(2)

    # Remove Whitespace in eval_id string
    eval_id.replace(" ","")
        

    return (regressionmode, eval_id, test_h_file, base_h_file, test_name, base_name)


# ========================================================================================
# ========================================================================================
#                                        Main
# ========================================================================================
# ========================================================================================

def main(argv):

    # Interpret the arguments to the script
    regressionmode, eval_id, test_h_file, base_h_file, test_name, base_name = interp_args(argv)

    # Close all figures
    plt.close('all')    

    plotfile_name = eval_id+"_mapplots.pdf"
    pdf = PdfPages(plotfile_name)

    # Load up a file to retrieve dimension info (fptest = file pointer test)
    fptest = netcdf.netcdf_file(test_h_file, 'r', mmap=False)

    if(regressionmode):
         fpbase = netcdf.netcdf_file(base_h_file, 'r', mmap=False)
         delta_str = 'Delta ({})-({})'.format(test_name.strip(),base_name.strip())
    
    # Load up the coordinate data
    latvec_in = fptest.variables['lat'].data;
    lonvec_in = fptest.variables['lon'].data;
    
    # Change coordinate system and create a re-order index array
    posids = np.where(lonvec_in>180.0)
    lonvec_in[posids] = -360.0+lonvec_in[posids]
    
    sort_ids=np.argsort(lonvec_in)
    lonvec_in=lonvec_in[sort_ids]

    # We will crop off the top and bottom of the f45, as those
    # points are at 90N and 90S? The coordinates we are creating
    # are going to be the 4 corners of each cell, so we end up having
    # one extra entry for each. Thus the longitudes end up with a size of
    # +1, and the latitude end up with a size of -2+1=-1

    nlat=latvec_in.size-1
    nlon=lonvec_in.size+1

    latvec = np.empty(nlat)
    lonvec = np.empty(nlon)

    dlon = lonvec_in[2]-lonvec_in[1]
    dlat = latvec_in[2]-latvec_in[1]
    lonvec[0] = np.maximum(-180.0,lonvec_in[0]-0.5*dlon)
    lonvec[1:-1] = 0.5*(lonvec_in[1:]+lonvec_in[0:-1])
    lonvec[-1] = np.minimum(lonvec[-2]+dlon,180.0)
    latvec = 0.5*(latvec_in[1:]+latvec_in[0:-1])

    # Create a mesh
    xv,yv = np.meshgrid(lonvec,latvec,sparse=False,indexing='xy')

    #land fraction
    landfrac = fptest.variables['landfrac'].data[1:-1,sort_ids]

    # Save the ocean-ids
    ocean_ids = np.where(landfrac>1.0)

    
    landfrac[ocean_ids]=np.nan

    #float PFTbiomass(time, fates_levpft, lat, lon) ;
    #	float PFTleafbiomass(time, fates_levpft, lat, lon) ;

    #(1, 46, 72)
    # Total Biomass
    tot_biomass_test = np.transpose(fptest.variables['ED_biomass'].data[0,1:-1,sort_ids])
    tot_biomass_test = tot_biomass_test * g_to_Mg / m2_to_ha
    tot_biomass_test[ocean_ids] = np.nan    # Set ocean-cells to nan

    if(regressionmode):
         
         tot_biomass_base = np.transpose(fpbase.variables['ED_biomass'].data[0,1:-1,sort_ids])
         tot_biomass_base = tot_biomass_base * g_to_Mg / m2_to_ha
         tot_biomass_base[ocean_ids] = np.nan    # Set ocean-cells to nan
         DeltaPlots(xv,yv,tot_biomass_base,tot_biomass_test,ylgn_seq_cmap,rdbu_div_cmap,'Total Biomass [Mg/ha]',delta_str,pdf)
    else:
         SingleMapPlot(xv,yv,tot_biomass_test,ylgn_seq_cmap,'Total Biomass [Mg/ha]',pdf)
    
   
         
    # (1, 46, 72)
    # Total LAI
    tlai_test = np.transpose(fptest.variables['TLAI'].data[0,1:-1,sort_ids])
    tlai_test[ocean_ids] = np.nan

    if(regressionmode):
         
         tlai_base = np.transpose(fpbase.variables['TLAI'].data[0,1:-1,sort_ids])
         tlai_base[ocean_ids] = np.nan    # Set ocean-cells to nan
         DeltaPlots(xv,yv,tlai_base,tlai_test,ylgn_seq_cmap,rdbu_div_cmap,'Total LAI [m2/m2]',delta_str,pdf)
    else:
         SingleMapPlot(xv,yv,tlai_test,ylgn_seq_cmap,'Total LAI [m2/m2]',pdf)
     


    # Index of dominant PFT by biomass
    # PFTbiomass(time, fates_levpft, lat, lon) 
    pftbiomass_test = fptest.variables['PFTbiomass'].data[0,:,1:-1,sort_ids]
    pft_bdom_test = np.ones(landfrac.shape)*np.nan
    npft = pftbiomass_test.shape[1]
    for ilat in range(0,landfrac.shape[0]):
         for ilon in range(0,landfrac.shape[1]):
              if( ~np.isnan(landfrac[ilat,ilon]) and np.amax(pftbiomass_test[ilon,:,ilat]) > 1.e-6 ):
                   maxids=np.argmax(pftbiomass_test[ilon,:,ilat])
                   pft_bdom_test[ilat,ilon] = maxids+1
    pft_cmap = discrete_cubehelix(npft)

    
         
    if(regressionmode):
         pftbiomass_base = fpbase.variables['PFTbiomass'].data[0,:,1:-1,sort_ids]
         pft_bdom_base = np.ones(landfrac.shape)*np.nan
         npft = pftbiomass_base.shape[1]
         for ilat in range(0,landfrac.shape[0]):
              for ilon in range(0,landfrac.shape[1]):
                   if( ~np.isnan(landfrac[ilat,ilon]) and \
                       np.amax(pftbiomass_base[ilon,:,ilat]) > 1.e-6 ):
                        maxids=np.argmax(pftbiomass_base[ilon,:,ilat])
                        pft_bdom_base[ilat,ilon] = maxids+1
         
         DoubleIndexMapPlot(xv,yv,pft_bdom_base,pft_bdom_test,pft_cmap,'Dominant PFT by Biomass',pdf)
    else:
         IndexMapPlot(xv,yv,pft_bdom_test,pft_cmap,'Dominant PFT by Biomass',pdf)
    


    # Loop through the PFTs and plot out their coverage fractions

    npft = pftbiomass_test.shape[1]
    for ipft in range(0,npft):
         
         # Biomass coverage fractions
         #pftbiomass_test = fptest.variables['PFTbiomass'].data[0,:,1:-1,sort_ids]
         onepft_test = np.ones(landfrac.shape)*np.nan
         for ilat in range(0,landfrac.shape[0]):
              for ilon in range(0,landfrac.shape[1]):
                   if( ~np.isnan(landfrac[ilat,ilon])):
                       onepft_test[ilat,ilon] = pftbiomass_test[ilon,ipft,ilat] / (100.*tot_biomass_test[ilat,ilon])
                       # Test if the sum is ok
                    
         
         SingleMapPlot(xv,yv,onepft_test,ylgn_seq_cmap,'Biomass Fraction, PFT {}'.format(ipft+1),pdf)



#    plt.show()
    pdf.close()
#    code.interact(local=dict(globals(), **locals())) 
    #code.interact(local=locals())
    
    print('Analysis Complete')
    print('Report generated in {}'.format(plotfile_name))


def SingleMapPlot(xv,yv,mapdata,color_map,map_title,pdf):

     fig = plt.figure()

     m = Basemap(projection='robin',lon_0=0,resolution='c')
     xmap,ymap = m(xv,yv)

     m.drawcoastlines()
     m.pcolormesh(xmap,ymap,np.ma.masked_invalid(mapdata),cmap=color_map)
     m.colorbar()
     m.drawparallels(np.arange(-90.,120.,30.))
     m.drawmeridians(np.arange(0.,360.,60.))
     plt.title(map_title)
     
     pdf.savefig(fig)


def IndexMapPlot(xv,yv,mapdata,color_map,map_title,pdf):

     fig = plt.figure()

     indexrange = color_map.N

     m = Basemap(projection='robin',lon_0=0,resolution='c')
     xmap,ymap = m(xv,yv)

     m.drawcoastlines()
     m.pcolormesh(xmap,ymap,np.ma.masked_invalid(mapdata),cmap=color_map,vmin=0.5,vmax=indexrange+0.5)
     m.colorbar(ticks=np.linspace(1,indexrange,indexrange))
     plt.title(map_title)
     
     pdf.savefig(fig)
     


def DeltaPlots(xv,yv,mapdata1,mapdata2,base_cmap,delta_cmap,map_title,delta_str,pdf):

     fig = plt.figure()

     ax = fig.add_subplot(211)
     ax.set_title('{}  (base)'.format(map_title))
     m = Basemap(projection='robin',lon_0=0,resolution='c')
     xmap,ymap = m(xv,yv)
     m.drawcoastlines()
     m.pcolormesh(xmap,ymap,np.ma.masked_invalid(mapdata1),cmap=base_cmap)
     m.colorbar()

     delta = np.ma.masked_invalid(mapdata2-mapdata1)

     crange = np.maximum(0.01,np.max(np.abs(delta)))


     ax = fig.add_subplot(212)
     ax.set_title(delta_str)
     m = Basemap(projection='robin',lon_0=0,resolution='c')
     xmap,ymap = m(xv,yv)
     m.drawcoastlines()
     m.pcolormesh(xmap,ymap,np.ma.masked_invalid(mapdata2-mapdata1),cmap=delta_cmap,vmin=-crange, vmax=crange)
     m.colorbar()
     
     pdf.savefig(fig)


def DoubleMapPlots(xv,yv,mapdata1,mapdata2,base_cmap,map_title,pdf):

     fig = plt.figure()

     crange_hi = np.nanmax( [np.nanmax(mapdata1),np.nanmax(mapdata2),0.01])
     crange_lo = np.nanmin( [np.nanmin(mapdata1),np.nanmin(mapdata2),-0.01])

     ax = fig.add_subplot(211)
     ax.set_title('{}  (base)'.format(map_title))
     m = Basemap(projection='robin',lon_0=0,resolution='c')
     xmap,ymap = m(xv,yv)
     m.drawcoastlines()
     m.pcolormesh(xmap,ymap,np.ma.masked_invalid(mapdata1),cmap=base_cmap,vmin=crange_lo,vmax=crange_hi)
     m.colorbar()

     ax = fig.add_subplot(212)
     ax.set_title('{}  (test)'.format(map_title))
     m = Basemap(projection='robin',lon_0=0,resolution='c')
     xmap,ymap = m(xv,yv)
     m.drawcoastlines()
     m.pcolormesh(xmap,ymap,np.ma.masked_invalid(mapdata2),cmap=base_cmap,vmin=crange_lo,vmax=crange_hi)
     m.colorbar()
     
     pdf.savefig(fig)

def DoubleIndexMapPlot(xv,yv,basedata,testdata,color_map,map_title,pdf):

     fig = plt.figure()

     indexrange = color_map.N

     ax = fig.add_subplot(211)
     ax.set_title('{} (Base)'.format(map_title))
     m = Basemap(projection='robin',lon_0=0,resolution='c')
     xmap,ymap = m(xv,yv)
     m.drawcoastlines()
     m.pcolormesh(xmap,ymap,np.ma.masked_invalid(basedata),cmap=color_map,vmin=0.5,vmax=indexrange+0.5)
     m.colorbar(ticks=np.linspace(1,indexrange,indexrange))

     ax = fig.add_subplot(212)
     ax.set_title('{} (Test)'.format(map_title))
     m = Basemap(projection='robin',lon_0=0,resolution='c')
     xmap,ymap = m(xv,yv)
     m.drawcoastlines()
     m.pcolormesh(xmap,ymap,np.ma.masked_invalid(testdata),cmap=color_map,vmin=0.5,vmax=indexrange+0.5)
     m.colorbar(ticks=np.linspace(1,indexrange,indexrange))
     
     pdf.savefig(fig)


def discrete_cubehelix(N):

    base = plt.cm.get_cmap('cubehelix')
    color_list = base(np.random.randint(0,high=255,size=N))
    cmap_name = base.name + str(N)
    return base.from_list(cmap_name, color_list, N)



# =======================================================================================
# This is the actual call to main
   
if __name__ == "__main__":
    main(sys.argv)
