# -*- coding: utf-8 -*-
"""
Insert module description/summary.

Provide any or all of the following:
1. extended summary
2. routine listings/functions/classes
3. see also
4. notes
5. references
6. examples

@author: j2cle
"""

# %% Imports
import numpy as np
import pandas as pd

# %% Code
def load_txt(file, header_ident='[[', data_ident="DATA", info_ident="ANALYSIS"):
    with open(file) as f:
        # contents = f.readlines()
        n=1
        headers=[]
        n_info = 0
        n_data = 0
        for line in f:
            if "[[" in line:
                headers.append(n)
            if "ANALYSIS" in line:
                n_info = n
            if "DATA" in line:
                n_data = n
            n += 1
            
    ind = np.argwhere(np.array(headers) == n_info)[0][0]
    info = pd.read_csv(file,sep="\**\s*\t", skiprows=headers[ind], nrows=headers[ind+1]-headers[ind]-1, index_col=0, usecols=[0,1,2], header=None)
    info = pd.DataFrame(info[1]).T
    
    ind = np.argwhere(np.array(headers) == n_data)[0][0]
    data = pd.read_csv(file,sep="\t", skiprows=headers[ind], nrows=headers[ind+1]-headers[ind]-4, usecols=[0,1])
    if data["Current (A)"][0] < -5:
        data["Current (A)"] = data["Current (A)"] * -1
    data["Current Density (mA/cm2)"] = (data["Current (A)"]*1e3)/float(info["A"])
    
    return data, info 

# %% Operations
if __name__ == "__main__":
    from pathlib import Path
    from research_tools.functions import save, p_find, load, f_find
    
    data_pth = p_find(
        "Dropbox (ASU)",
        "Work Docs",
        "Data",
        "Raw",
        "IV_SolarSim",
        "Leakage_Test1",
        base="home",
    )
    
    save_pth = p_find(
        "Dropbox (ASU)",
        "Work Docs",
        "Data",
        "Analysis",
        "IV",
        "Leakage_tests",
        base="home",
    )
    
    files  = f_find(p_find(
        "Dropbox (ASU)",
        "Work Docs",
        "Data",
        "Raw",
        "IV_SolarSim",
        "Leakage_Test1",
        base="home",
    ))
    
    info_res = {}
    data_res = {}
    for file in files:
        with open(file) as f:
            # contents = f.readlines()
            n=1
            headers=[]
            n_info = 0
            n_data = 0
            # ind_info = []
            # ind_data = []
            for line in f:
                if "[[" in line:
                    headers.append(n)
                if "analysis" in line.lower():
                    n_info = n
                if "data" in line.lower():
                    n_data = n
                n += 1
                
        ind = np.argwhere(np.array(headers) == n_info)[0][0]
        info = pd.read_csv(file,sep="\**\s*\t", skiprows=headers[ind], nrows=headers[ind+1]-headers[ind]-1, index_col=0, usecols=[0,1,2], header=None)
        info = pd.DataFrame(info[1]).T
        
        ind = np.argwhere(np.array(headers) == n_data)[0][0]
        data = pd.read_csv(file,sep="\t", skiprows=headers[ind], nrows=headers[ind+1]-headers[ind]-4, usecols=[0,1])
        if data["Current (A)"][0] < -5:
            data["Current (A)"] = data["Current (A)"] * -1
        data["Current Density (mA/cm\+(2))"] = (data["Current (A)"]*1e3)/float(info["A"])
        
        info_res[file.stem] = info
        data_res[file.stem] = data
    
    # save(info_res,save_pth, "info_r1")
    # save(data_res,save_pth, "data_r1")