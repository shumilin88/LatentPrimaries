import os, glob, re
import itertools
from collections import defaultdict

import numpy as np
from scipy.spatial import Delaunay

from plotly import tools
import plotly.offline as py
import plotly.graph_objs as go
import plotly.figure_factory as FF
# py.init_notebook_mode(connected=True)

from SimDataDB import SimDataDB


def list_files(fpattern):
    files = glob.glob(fpattern)
    grab_digit = lambda f : int(re.search("([0-9]*)\.[a-zA-Z]*$",f).groups()[-1])
    files.sort(key=lambda f: grab_digit(f) )
    return files

def make_tri_plot(x,y,z, simplices, c=None, offset=(0,0), name='', **kwargs):
    return go.Mesh3d(x=x+1.5*offset[0],y=y,z=z+1.5*offset[1],
                     i=simplices[:,0],j=simplices[:,1],k=simplices[:,2],
                     intensity=c/np.max(c),
                     name=name,showscale = True,**kwargs)

def plot_ptrho(D,simplices,colorby=-1,offset=(0,0), name='', **kwargs):
    return make_tri_plot(D[:,0],D[:,1],D[:,2], simplices, c=D[:,colorby],
                        offset=offset,name=name,**kwargs)

def plot_qqrho(D,simplices,colorby=-1,offset=(0,0), name='', **kwargs):
    return make_tri_plot(D[:,4],D[:,5],D[:,2], simplices, c=D[:,colorby],
                        offset=offset,name=name,**kwargs)

def plot_qq_Tprhoh(D,simplices,colorby=-1,offset=(0,0), name='', **kwargs):
    plts = []
#     subfig = tools.make_subplots(rows=2,cols=2,
#         subplot_titles=('T','p','rho','h'),
#         specs=[
#         [{'is_3d': True}, {'is_3d': True}],
#         [{'is_3d': True}, {'is_3d': True}]
#     ])

    for i in range(4):
        offset_i = (offset[0] + 2*(i%2), offset[1] + 1.25*(i/2))
        print(offset_i)
        tp = make_tri_plot(D[:,4],D[:,5],D[:,i], simplices, c=D[:,colorby],
                        offset=offset_i,name=name,**kwargs)
#         subfig.append_trace(tp,1+i%2,1+i/2)
        plts.append(tp)
    # return subfig
    return plts


def read_networks(training_dir):
    archs = os.listdir(training_dir)
    archs.sort()
    
    surfaces = {}
    for arch in archs:
        files = list_files(training_dir+'/'+arch+'/surf_*.csv')
        try:
            dat = np.loadtxt(files[-1],delimiter=",",skiprows=1)
            surfaces[arch] = ( dat, Delaunay(dat[:,4:6]).simplices )
        except:
            dat = np.zeros((3,7))
            surfaces[arch] = ( dat, [] )
    return surfaces

def generate_trisurf_plots(surfaces):
    return [ (n,go.Figure(data=[plot_ptrho(d,simp,name=n)]))
             for n,(d,simp) in surfaces.items() ]

def plot_networks(surfaces,prefix=''):
    offs = range(int(np.ceil(len(surfaces)**0.5)))
    offsets = list(itertools.product(offs,offs))
    
    ptrhos = [ plot_ptrho(d,simp,offset=o,name=n)
               for (n,(d,simp)),o in zip(surfaces.items(),offsets) ]
    fig = go.Figure(data=ptrhos)
    return fig

#     qqrhos = [ plot_qqrho(d,simp,offset=o,name=n) 
#                for (n,(d,simp)),o in zip(surfaces.items(),offsets) ]
#     fig = go.Figure(data=ptrhos)
#     py.plot(fig,filename=prefix+'networks_q.html')
    

def plot_one_simulation(sdb, eos_name, problem, colorkey=None):
    networks = sdb.Query('select distinct network from {0}'.format(eos_name))
    legends = ['T','p','rho','h']
    Nfields = len(legends)
    gridx, gridy = 1,Nfields
    showleg = defaultdict(lambda : True)
    if colorkey is None:
        colorring = itertools.cycle(['black','orange','purple','red','blue','green'])
        colorkey = defaultdict(lambda : colorring.next())
    subfig = tools.make_subplots(rows=gridy,cols=gridx,
                                 shared_xaxes=True,shared_yaxes=False)
    res = sdb.Query(
            'select network,series from {eos_name} where problem="{0}"'.
            format(problem,eos_name=eos_name))
    for i,name in enumerate(legends):
        for n,t in res:
            trace = go.Scatter(x=t[:,0],y=t[:,i+3],name=n,legendgroup=n,
                               mode='lines',
                               line=dict(color=colorkey[n]),
                               showlegend=showleg[n])
            showleg[n]=False
            subfig.append_trace(trace,1+i,1)
#     print(subfig)
    return subfig

def make_simulation_plot_list(database,eos_name):
    colorring = itertools.cycle(['black','orange','purple','red','blue','green'])
    colorkey = defaultdict(lambda : colorring.next())
    sdb = SimDataDB(database)
    problems = sdb.Query('select distinct problem from {0}'.format(eos_name))
    print problems
    plots = [ plot_one_simulation(sdb,eos_name, p[0], colorkey=colorkey) 
             for p in problems ]
    return plots

        
def plot_simulations(database,eos_name,prefix=''):
    """Plot all of the test simulations in a grid"""
    sdb = SimDataDB(database)
    problems = sdb.Query('select distinct problem from {0}'.format(eos_name))
    networks = sdb.Query('select distinct network from {0}'.format(eos_name))
    print(problems)
    showleg = defaultdict(lambda : True)
    colorring = itertools.cycle(['black','orange','purple','red','blue','green'])
    colorkey = defaultdict(lambda : colorring.next())
    numproblems=len(problems)
    gridx = int(numproblems**0.5)+1
    gridy = int(numproblems / gridx)+1
    positions = list(itertools.product(range(1,gridx+1),range(1,gridy+1)))

#     titles, titles_trans = [], range(4*gridx*gridy)
#     for prob in problems:
#         titles.extend([prob[0]] + ['_' for _ in range(4-1) ])
#     for i in range(4*gridx):
#         for j in range(gridy):
#             titles_trans[j*4*gridx+i] = titles[4*i*gridy+j]
    titles = ['' for _ in range(4*gridx*gridy)]
    for p,pos in zip(problems,positions):
        #titles[4*gridx*(pos[1]-1)+(pos[0]-1)+1] = p[0]
        titles[4*gridy*(pos[0]-1)+(pos[1]-1)] = p[0]
    subfig = tools.make_subplots(rows=4*gridx,cols=gridy,
                  shared_xaxes=False, shared_yaxes=False,
                  subplot_titles=titles)
    for p,pos in zip(problems,positions):
        res = sdb.Query(
            'select network,series from {eos_name} where problem="{0}"'.
            format(p[0],eos_name=eos_name))
        legends=['T','p','rho','h']
        #print p[0]
        for i,name in enumerate(legends):
            for n,t in res:
                trace = go.Scatter(x=t[:,0],y=t[:,i+3],name=n,legendgroup=n,
                                   mode='lines',
                                   line=dict(color=colorkey[n]),
                                   showlegend=showleg[n])
                showleg[n]=False
                subfig.append_trace(trace,4*(pos[0]-1)+i+1,pos[1])
#     from IPython import embed ; embed()
    return subfig
    
if __name__=='__main__':
    hub = "/Users/afq/Google Drive/networks/"
    eoses = [
        "water_slgc_logp_64",
        "water_lg",
        "water_linear",
    ]
    report_dir = hub+"report/"
    try:
        os.mkdir(report_dir)
    except OSError:
        pass
    for eos in eoses:
        prefix = report_dir+eos+'_'
#         surfs = read_networks(hub+'training_'+eos)
        
#         netplots = plot_networks(surfs)
#         py.plot(fig,filename=prefix+'networks.html')
        
        simplots = plot_simulations(hub+'test_databases/'+eos+'_testing.db',eos)
        py.plot(simplots, filename=prefix+'simulation_tests.html')
        
#         qqplot = plot_qq_Tprhoh(*surfs['Classifying_2,4,12,24,sigmoid (1)']) 
#         py.plot(go.Figure(qqplot), filename=prefix+'qq_plots.html')
        