# -*- coding: utf-8 -*-
"""
Created on Tue Sep 15 14:08:01 2020

@author: j2cle
"""
import os
import utilities as ut
import iv_analysis_functions_dd_pso as iaf

mainpath = ut.pathify("work", "Data", "Analysis", "IV")
# folderstodo = ["DOW4-2"]
folderstodo = ["DOW8", "DOW7", "DOW6", "DOW5"]
myfolders = [os.sep.join((mainpath, x)) for x in folderstodo]

for findex in range(len(myfolders)):
    infilename = "".join(("Result_log_", folderstodo[findex], ".xlsx"))
    outfilename = "".join(("Result_final_", folderstodo[findex], ".xlsx"))

    iaf.iv_stats_dd(myfolders[findex], infilename, outfilename)
