""" Created on Thu Aug 13 08:54:41 2020
@author: j2cle
"""

import os
import warnings
import random
import openpyxl
import pandas as pd
import numpy as np
import utilities as ut
import matplotlib.pyplot as plt
import iv_analysis_functions_dd_pso as iaf
from scipy import optimize
from scipy.stats import linregress
from datetime import datetime, timedelta

warnings.filterwarnings("ignore", "The iteration is not making good progress")
np.seterr(divide="ignore", invalid="ignore")

timestamp = datetime.now().strftime("%Y%m%d_%H-%M")

print_file = ut.pathify("work", "Python Scripts", "Prints", f"{timestamp}.txt")

# ----- Input Parameters -----
Mod_T = ut.Temp(25, "C").K  # Temp for part 2

# ----- Constants -----
c_time_interval = 10

c_l_total_iter = 20000
c_target_error = 2.5e-5
c_particles_per_dim = 5


c_weight_max = 0.95
c_weight_min = 1.003
c_m_vmax = 100  # Rsh in Vmax multiplier
c_m_velocity = 1e-2  # low velocity multiplier--> 1% of boundry size
c_l_slower = 5e-4  # when to apply low velocity manipulation
c_l_slow = 1e-2  # c_l_slower but for Rsh

# full cell values
c_area_cell = (15.6) ** 2
c_area_mask = (14) ** 2

l_cut_short = 1
l_skip_dark = 0
l_skip_diode = 0
l_skip_light = 0
l_ignore_area = 0
l_check = 0
save_gbest = 1

c_cut_short = 20  # was 500
c_JL_perc_init = 0.015
c_Rs_perc_init = 0.5
c_Rsh_perc_init = 0.7
c_J0_perc_init = 0.1
c_n_min = 1
c_n1_max = 2
c_n2_max = 3
c_J0_min = 6
c_J0_max = 18

# area = (15.6)**2
# c_Rsh_test = 101080

# ----- Import Data -----

mainpath = ut.pathify("work", "Data", "Analysis", "IV")
folderstodo = ["DOW4-2", "DOW3-2"]
# folderstodo = ['Viko9','Viko8','Viko7','Viko6']
myfolders = [os.sep.join((mainpath, x)) for x in folderstodo]

for mypath in myfolders:

    for (dirpath, dirnames, filenames) in os.walk(mypath):
        break
    filepaths = mypath

    files = []
    jvst_files = []
    i = 0
    for filename in os.listdir(filepaths[:]):
        if filename.endswith("jvtst"):
            files.insert(i, os.path.join(str(filepaths[:]), str(filename)))
            jvst_files.insert(i, str(filename))
            #        print(files.index(files[i]), files[i])
            i += 1
    # Data must be compiled prior to evaluation.  If this file does not exist or new
    # files are missing, the compiler is run then the file is imported
    if "Compiled.xlsx" in filenames:
        df = pd.ExcelFile(os.sep.join((mypath, "Compiled.xlsx")))

        if len(df.sheet_names) != 2 * len(jvst_files):
            iaf.compiler(mypath)
            df = pd.ExcelFile(os.sep.join((mypath, "Compiled.xlsx")))
    else:
        iaf.compiler(mypath)
        df = pd.ExcelFile(os.sep.join((mypath, "Compiled.xlsx")))
    # Prepares the dataframe for results
    Result_cols = [
        "Date-Time",
        "Voc [V]",
        "Jsc [A/cm2]",
        "FF [%]",
        "Vmp [V]",
        "Jmp [A/cm2]",
        "Pmp [W/cm2]",
        "Rs [ohm-cm2]",
        "Rsh (slope)[ohm-cm2]",
        "Rsh (dark)[ohm-cm2]",
        "Rsh (light)[ohm-cm2]",
        "J01 [A/cm2]",
        "n1",
        "J02 [A/cm2]",
        "n2",
        "RMSE",
    ]

    list_params_all = [
        "JL [A/cm2]",
        "Rs [ohm-cm2]",
        "Rsh [ohm-cm2]",
        "J01 [A/cm2]",
        "n1",
        "J02 [A/cm2]",
        "n2",
        "RMSE",
    ]

    infilename = "Result_log_" + folderstodo[myfolders.index(mypath)]
    if f"{infilename}.xlsx" in filenames:
        prev_results = pd.read_excel(os.sep.join((mypath, f"{infilename}.xlsx")), index_col=0)
    else:
        l_cut_short = 0
        prev_results = pd.DataFrame(columns=Result_cols)
    prev_results["Date-Time"] = pd.to_datetime(prev_results["Date-Time"], yearfirst=True)
    prev_results[Result_cols[1:]] = prev_results[Result_cols[1:]].astype(float)

    wb = openpyxl.Workbook()
    # wb2 = openpyxl.Workbook()

    res_compiled = pd.DataFrame(columns=Result_cols, index=df.sheet_names)

    res_compiled["Date-Time"] = pd.to_datetime(res_compiled["Date-Time"], yearfirst=True)
    res_compiled[Result_cols[1:]] = res_compiled[Result_cols[1:]].astype(float)

    # ----- Primary loop -----
    # Cycles through each file
    # for indexer in range(0, len(df.sheet_names)):
    for indexer in reversed(range(0, len(df.sheet_names))):
        # Returns a datetime object containing the local date and time
        t_run_time_start = datetime.now()

        # Get pertinet data from files
        for get_name in range(0, len(files)):
            if jvst_files[get_name][15:-6] in df.sheet_names[indexer]:
                date = jvst_files[get_name][0:6]
                time = jvst_files[get_name][7:13]
                date_time = date + " " + time
                res_p0 = [date_time]
        # Get name of file
        name = df.sheet_names[indexer]
        ut.myprint(print_file, "-->", name)

        # ----- Initial IV's -----
        # Bring in previous data set results if desired
        if len(prev_results) != 0 and indexer < len(prev_results):
            if prev_results.iloc[indexer, -1] > c_target_error * c_cut_short:
                l_cut = 0
                l_check = 1
            elif pd.isnull(prev_results.iloc[indexer, -1]):
                l_cut = 0
            else:
                l_cut = l_cut_short
        else:
            l_cut = l_cut_short
        # Bring in previous data set results if desired
        if name in prev_results.index.to_numpy() and l_cut == 1:
            print("Copied")
            res_compiled.loc[name, Result_cols] = prev_results.loc[name].to_numpy(copy=True)
            save_gbest = 0

            # Import Data
            df_data_base_info = pd.read_excel(
                os.sep.join((mypath, "Compiled.xlsx")),
                sheet_name=indexer,
                header=None,
                usecols="E,F",
                index_col=0,
                skiprows=2,
            ).dropna()
            df_data_elec_info = pd.read_excel(
                os.sep.join((mypath, "Compiled.xlsx")),
                sheet_name=indexer,
                header=None,
                usecols="G,H,I",
                index_col=0,
                skiprows=2,
            ).dropna()

            l_area_init = df_data_base_info.index[
                ["area" in x.lower() for x in df_data_base_info.index]
            ].to_numpy()[0]
            c_area_init = float(df_data_base_info.loc[l_area_init, :].to_numpy()[0])

            if l_ignore_area:
                c_area_mask = c_area_init
                c_area_cell = c_area_init
            df_data_raw_light_iv = pd.read_excel(
                os.sep.join((mypath, "Compiled.xlsx")),
                sheet_name=indexer,
                header=1,
                names=["Volt (V)", "J(A/sqcm)"],
                usecols="A,B",
            ).dropna()
            df_data_raw_dark_iv = pd.read_excel(
                os.sep.join((mypath, "Compiled.xlsx")),
                sheet_name=indexer,
                header=1,
                names=["Volt (V)", "J(A/sqcm)"],
                usecols="C,D",
            ).dropna()

            df_data_raw_light_iv["J(A/sqcm)"] = (
                df_data_raw_light_iv["J(A/sqcm)"] * -1 * c_area_init / c_area_mask
            )
            df_data_raw_dark_iv["J(A/sqcm)"] = (
                df_data_raw_dark_iv["J(A/sqcm)"] * c_area_init / c_area_cell
            )

            df_data_exp_light_iv = pd.DataFrame(
                df_data_raw_light_iv.loc[
                    (df_data_raw_light_iv["Volt (V)"] >= 0)
                    & (df_data_raw_light_iv["J(A/sqcm)"] >= 0)
                ].to_numpy(),
                columns=["Volt (V)", "J(A/sqcm)"],
            )
            df_data_exp_dark_iv = pd.DataFrame(
                df_data_raw_dark_iv.loc[
                    (df_data_raw_dark_iv["Volt (V)"] >= 0) & (df_data_raw_dark_iv["J(A/sqcm)"] >= 0)
                ].to_numpy(),
                columns=["Volt (V)", "J(A/sqcm)"],
            )

            # Find initial params
            (
                var_IV_Voc,
                var_IV_Jsc,
                var_IV_FF,
                var_IV_Vmp,
                var_IV_Jmp,
                var_IV_Pmp,
            ) = ut.cell_params(
                df_data_exp_light_iv.iloc[:, 0].to_numpy(),
                df_data_exp_light_iv.iloc[:, 1].to_numpy(),
            )

            list_params_copy = [
                "Jsc [A/cm2]",
                "Rs [ohm-cm2]",
                "Rsh (light)[ohm-cm2]",
                "J01 [A/cm2]",
                "n1",
                "J02 [A/cm2]",
                "n2",
            ]
            list_params_return = [
                "Voc [V]",
                "FF [%]",
                "Vmp [V]",
                "Jmp [A/cm2]",
                "Pmp [W/cm2]",
            ]

            data_in_fit = prev_results.loc[name, list_params_copy].to_numpy(float)
            data_in_fit[[3, 5]] = np.log10(data_in_fit[[3, 5]]) * -1

            data_fit_volt_real = np.linspace(0, var_IV_Voc + var_IV_Voc * 0.05, 1000)
            data_fit_curr_real_init = np.array(
                [
                    np.interp(
                        x,
                        df_data_exp_light_iv.iloc[:, 0].to_numpy(),
                        df_data_exp_light_iv.iloc[:, 1].to_numpy(),
                    )
                    for x in data_fit_volt_real
                ]
            )

            data_fit_curr_real = np.array(
                [
                    optimize.fsolve(
                        iaf.double_diode_cost,
                        data_fit_curr_real_init[x],
                        (data_fit_volt_real[x], data_in_fit),
                        xtol=1e-12,
                    )[0]
                    for x in range(len(data_fit_volt_real))
                ]
            )

            res_compiled.loc[name, list_params_return] = np.array(
                ut.cell_params(data_fit_volt_real, data_fit_curr_real)
            )[[0, 2, 3, 4, 5]]
        # Start calculation of new data data set
        else:

            ut.myprint(print_file, "Started: ", t_run_time_start)

            # Import Data
            df_data_base_info = pd.read_excel(
                os.sep.join((mypath, "Compiled.xlsx")),
                sheet_name=indexer,
                header=None,
                usecols="E,F",
                index_col=0,
                skiprows=2,
            ).dropna()
            df_data_elec_info = pd.read_excel(
                os.sep.join((mypath, "Compiled.xlsx")),
                sheet_name=indexer,
                header=None,
                usecols="G,H,I",
                index_col=0,
                skiprows=2,
            ).dropna()

            l_area_init = df_data_base_info.index[
                ["area" in x.lower() for x in df_data_base_info.index]
            ].to_numpy()[0]
            c_area_init = float(df_data_base_info.loc[l_area_init, :].to_numpy()[0])

            if l_ignore_area:
                c_area_mask = c_area_init
                c_area_cell = c_area_init
            df_data_raw_light_iv = pd.read_excel(
                os.sep.join((mypath, "Compiled.xlsx")),
                sheet_name=indexer,
                header=1,
                names=["Volt (V)", "J(A/sqcm)"],
                usecols="A,B",
            ).dropna()
            df_data_raw_dark_iv = pd.read_excel(
                os.sep.join((mypath, "Compiled.xlsx")),
                sheet_name=indexer,
                header=1,
                names=["Volt (V)", "J(A/sqcm)"],
                usecols="C,D",
            ).dropna()

            df_data_raw_light_iv["J(A/sqcm)"] = (
                df_data_raw_light_iv["J(A/sqcm)"] * -1 * c_area_init / c_area_mask
            )
            df_data_raw_dark_iv["J(A/sqcm)"] = (
                df_data_raw_dark_iv["J(A/sqcm)"] * c_area_init / c_area_cell
            )

            df_data_exp_light_iv = pd.DataFrame(
                df_data_raw_light_iv.loc[
                    (df_data_raw_light_iv["Volt (V)"] >= 0)
                    & (df_data_raw_light_iv["J(A/sqcm)"] >= 0)
                ].to_numpy(),
                columns=["Volt (V)", "J(A/sqcm)"],
            )
            df_data_exp_dark_iv = pd.DataFrame(
                df_data_raw_dark_iv.loc[
                    (df_data_raw_dark_iv["Volt (V)"] >= 0) & (df_data_raw_dark_iv["J(A/sqcm)"] >= 0)
                ].to_numpy(),
                columns=["Volt (V)", "J(A/sqcm)"],
            )

            # Find initial params
            (
                var_IV_Voc,
                var_IV_Jsc,
                var_IV_FF,
                var_IV_Vmp,
                var_IV_Jmp,
                var_IV_Pmp,
            ) = ut.cell_params(
                df_data_exp_light_iv.iloc[:, 0].to_numpy(),
                df_data_exp_light_iv.iloc[:, 1].to_numpy(),
            )

            # ----- Approximate ressistance values -----
            # performs linear regression on the data to get the slope fit of the
            # respecive regions
            var_lim_shunt = df_data_exp_dark_iv.index[
                df_data_exp_dark_iv["Volt (V)"] <= 0.1
            ].to_numpy()[-1]
            var_lim_series = df_data_exp_light_iv.index[
                df_data_exp_light_iv["Volt (V)"] <= (var_IV_Voc - 0.05)
            ].to_numpy()[-1]
            var_Rsh_slope = (
                1
                / linregress(
                    df_data_exp_dark_iv.iloc[:var_lim_shunt, 0].to_numpy(),
                    df_data_exp_dark_iv.iloc[:var_lim_shunt, 1].to_numpy(),
                )[0]
            )
            var_Rs_slope = (
                -1
                / linregress(
                    df_data_exp_light_iv.iloc[var_lim_series:, 0].to_numpy(),
                    df_data_exp_light_iv.iloc[var_lim_series:, 1].to_numpy(),
                )[0]
            )

            if var_Rsh_slope <= 0:
                ut.myprint(print_file, var_Rsh_slope)
                var_Rsh_slope = 1e5 / c_area_cell
            # print results
            ut.myprint(print_file, "Rseries slope = ", var_Rs_slope)
            ut.myprint(print_file, "Rshunt slope = ", var_Rsh_slope)

            # ----- First PSO: Dark data -----

            t_dark_time_start = datetime.now()
            # establish how many sharks you want
            var_n_particles = c_particles_per_dim * 4

            # establish which sharks are evaluated and which are bull sharks (fast)
            # and which are basking sharks (slow)
            list_params_active = list_params_all[1:-3]
            list_params_fast = ["Rsh [ohm-cm2]"]
            list_params_slow = ["Rs [ohm-cm2]", "J01 [A/cm2]", "n1"]

            if var_Rsh_slope < 100 and var_Rs_slope > 3:
                var_Rs_slope_init = 2
                c_J0_perc_init = 0.5
                c_n1_max = 3
                c_n2_max = 5
                c_J0_min = 4
                c_J0_max = 20
                l_shunted = 1
            else:
                var_Rs_slope_init = var_Rs_slope
                l_shunted = 0
            # set up initial guesses; Rs, Rsh, J01, and n1 are based off dark pso
            df_dark_inits = pd.DataFrame(columns=list_params_all)
            df_dark_inits.loc[0] = np.array([0, var_Rs_slope_init, var_Rsh_slope, 12, 1, 0, 0, 1])

            # establish boudaries or size of the ocean.  Rsh: boundary allow eval of
            # guess by slope and guess by dark IV;
            df_dark_bounds = pd.DataFrame(
                np.array(
                    [
                        [0, 0],
                        [
                            df_dark_inits.iloc[0, 1] * (1 - c_Rs_perc_init),
                            df_dark_inits.iloc[0, 1] * (1 + c_Rs_perc_init),
                        ],
                        [
                            df_dark_inits.iloc[0, 2] * (1 - c_Rsh_perc_init),
                            df_dark_inits.iloc[0, 2] * (1 + c_Rsh_perc_init),
                        ],
                        [c_J0_min, c_J0_max],
                        [c_n_min, c_n1_max],
                        [0, 0],
                        [0, 0],
                        [0, 1],
                    ]
                ).T,
                index=["Low", "High"],
                columns=list_params_all,
            )

            # Establish max velocity.  Not needed when boundaries used on sharks,
            # repurposed to ensure movement is maintained
            df_dark_vmax = pd.DataFrame(columns=list_params_all[1:-3])
            df_dark_vmax.loc[0] = 0.5 * (
                np.array(
                    [
                        np.diff(df_dark_bounds["Rs [ohm-cm2]"])[0],
                        np.diff(df_dark_bounds["Rsh [ohm-cm2]"])[0],
                        np.diff(df_dark_bounds["J01 [A/cm2]"])[0],
                        np.diff(df_dark_bounds["n1"])[0],
                    ]
                )
            )  # *c_m_vmax

            # this is the school of sharks
            df_dark_particles = pd.DataFrame(
                np.array(
                    [
                        np.array(
                            [
                                0,
                                np.random.triangular(
                                    df_dark_bounds.loc["Low", "Rs [ohm-cm2]"],
                                    df_dark_inits.iloc[0, 1],
                                    df_dark_bounds.loc["High", "Rs [ohm-cm2]"],
                                ),
                                np.random.triangular(
                                    df_dark_bounds.loc["Low", "Rsh [ohm-cm2]"],
                                    df_dark_inits.iloc[0, 2],
                                    df_dark_bounds.loc["High", "Rsh [ohm-cm2]"],
                                ),
                                np.random.triangular(
                                    df_dark_bounds.loc["Low", "J01 [A/cm2]"],
                                    df_dark_inits.iloc[0, 3],
                                    df_dark_bounds.loc["High", "J01 [A/cm2]"],
                                ),
                                np.random.triangular(
                                    df_dark_bounds.loc["Low", "n1"],
                                    df_dark_inits.iloc[0, 4],
                                    df_dark_bounds.loc["High", "n1"],
                                ),
                                0,
                                0,
                                1e20,
                            ]
                        )
                        for _ in range(var_n_particles)
                    ]
                ),
                columns=list_params_all,
            )

            # initialize other needed dataframes
            df_dark_pbest = pd.DataFrame(
                np.array(
                    [
                        [
                            0,
                            df_dark_inits.iloc[0, 1],
                            df_dark_inits.iloc[0, 2],
                            df_dark_inits.iloc[0, 3],
                            df_dark_inits.iloc[0, 4],
                            0,
                            0,
                            1e20,
                        ]
                        for _ in range(var_n_particles)
                    ]
                ),
                columns=list_params_all,
            )
            df_dark_gbest = pd.DataFrame(np.ones((1, 8)) * 1e100, columns=list_params_all)
            df_dark_velocities = pd.DataFrame(
                np.array([np.zeros((4)) for _ in range(var_n_particles)]),
                columns=list_params_all[1:-3],
            )

            # primary for loop which cycles through posiblities to find best values
            iter_gbest = 0
            for iter_pso in range(c_l_total_iter):

                # Checks sharks to make sure that they're in the right area
                for iter_dim in list_params_active:

                    # code: for a given dimension generates array of indexes where
                    # the value is outside the bands for high and low cases
                    arr_high_parts = df_dark_particles.index[
                        (df_dark_particles[iter_dim] >= df_dark_bounds.loc["High", iter_dim])
                    ].to_numpy()
                    arr_low_parts = df_dark_particles.index[
                        (df_dark_particles[iter_dim] <= df_dark_bounds.loc["Low", iter_dim])
                    ].to_numpy()

                    for iter_test_high in arr_high_parts:
                        if (
                            np.mean(
                                np.array(
                                    [
                                        df_dark_pbest.loc[iter_test_high, iter_dim],
                                        df_dark_bounds.loc["High", iter_dim],
                                    ]
                                )
                            )
                            > df_dark_bounds.loc["High", iter_dim]
                        ):
                            df_dark_pbest.loc[iter_test_high, iter_dim] = df_dark_bounds.loc[
                                "High", iter_dim
                            ]
                    for iter_test_low in arr_low_parts:
                        if (
                            np.mean(
                                np.array(
                                    [
                                        df_dark_pbest.loc[iter_test_low, iter_dim],
                                        df_dark_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            )
                            < df_dark_bounds.loc["Low", iter_dim]
                        ):
                            df_dark_pbest.loc[iter_test_low, iter_dim] = df_dark_bounds.loc[
                                "Low", iter_dim
                            ]
                    # code: applys triangular randomizer function to preferentially
                    # return them between the personal best and the boundary they
                    # crossed.
                    df_dark_particles.loc[arr_high_parts, iter_dim] = [
                        np.random.triangular(
                            np.mean(
                                np.array(
                                    [
                                        df_dark_pbest.loc[x, iter_dim],
                                        df_dark_vmax.loc[0, iter_dim]
                                        + df_dark_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            ),
                            np.mean(
                                np.array(
                                    [
                                        df_dark_pbest.loc[x, iter_dim],
                                        df_dark_bounds.loc["High", iter_dim],
                                    ]
                                )
                            ),
                            df_dark_bounds.loc["High", iter_dim],
                        )
                        for x in arr_high_parts
                    ]
                    df_dark_particles.loc[arr_low_parts, iter_dim] = [
                        np.random.triangular(
                            df_dark_bounds.loc["Low", iter_dim],
                            np.mean(
                                np.array(
                                    [
                                        df_dark_pbest.loc[x, iter_dim],
                                        df_dark_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            ),
                            np.mean(
                                np.array(
                                    [
                                        df_dark_pbest.loc[x, iter_dim],
                                        df_dark_vmax.loc[0, iter_dim]
                                        + df_dark_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            ),
                        )
                        for x in arr_low_parts
                    ]
                # Calculates the fit of the shark's current location
                df_dark_particles.loc[:, "RMSE"] = [
                    iaf.double_diode_pso(
                        df_dark_particles.iloc[x, :-1].to_numpy(), df_data_exp_dark_iv
                    )
                    for x in range(var_n_particles)
                ]

                # This is the pbest dataframe and stores the best position of each
                # shark
                # code: directly indexes the sharks have moved to more food in both
                # lists and tranferse the info to pbest
                df_dark_pbest.loc[
                    df_dark_particles["RMSE"] < df_dark_pbest["RMSE"], :
                ] = df_dark_particles.loc[df_dark_particles["RMSE"] < df_dark_pbest["RMSE"], :]

                # This loop stores the schools best positions ever.  To  reduce
                # processing time, can be saved as a single vector
                # Currently the df grows and saves updated gbest in new row.  This
                # allows for evaluation of the movement of the group in real time
                # (in spyder)
                if df_dark_gbest.iloc[-1, -1] > np.min(df_dark_particles["RMSE"]):
                    df_dark_gbest.loc[iter_gbest] = df_dark_particles[
                        df_dark_particles["RMSE"] == np.min(df_dark_particles["RMSE"])
                    ].values.tolist()[0]
                    iter_gbest += 1
                    var_dark_iters = iter_pso
                # If target error is reached, time interval is reached, or logic
                # indicates to skip, for loop is cut prematurely
                if (
                    (df_dark_gbest.iloc[-1, -1] < c_target_error)
                    or datetime.now() > t_dark_time_start + timedelta(minutes=c_time_interval / 3)
                    or l_skip_dark
                ):
                    break
                # updating variable which weights the sharks momentum.  Decreases
                # exponentially as interations increase.  This increases the impact
                # of the sharks best position and the schools best position as
                # iterations increase
                var_weight = c_weight_max * c_weight_min ** (-iter_pso)

                # Calculates velocity of each shark combining its current momentum,
                # its best position, and the schools best position
                # code: compares the best postions to the current position arrays and
                # incorporates a randomizer to keep the posibilities high
                df_dark_velocities.iloc[:, :] = (
                    (var_weight * df_dark_velocities.to_numpy())
                    + (2 * np.random.random())
                    * (
                        df_dark_pbest.iloc[:, 1:-3].to_numpy()
                        - df_dark_particles.iloc[:, 1:-3].to_numpy()
                    )
                    + (2 * np.random.random())
                    * (
                        df_dark_gbest.iloc[-1, 1:-3].to_numpy()
                        - df_dark_particles.iloc[:, 1:-3].to_numpy()
                    )
                )

                # Ensures all particles keep moving, if slowly --> basking sharks
                # code: generates array of the index for all basking sharks that are
                # on average moving slower than c_l_slower
                #       then applies a randomized multiplier to give them more
                # momentum.  Due to averaging, some may come to a stop until the
                # average matches desired cond
                arr_slower_parts = df_dark_velocities.index[
                    (
                        df_dark_velocities[list_params_slow].abs().to_numpy()
                        / df_dark_vmax.loc[0, list_params_slow].to_numpy()
                    ).mean(axis=1)
                    < c_l_slower
                ].to_numpy()
                df_dark_velocities.loc[arr_slower_parts, list_params_slow] = [
                    [
                        df_dark_vmax.loc[0, y]
                        * c_m_velocity
                        / 0.5
                        * (-1) ** (bool(random.getrandbits(1)))
                        * np.random.random()
                        for y in list_params_slow
                    ]
                    for _ in arr_slower_parts
                ]

                # code to ensure all particles have a lot of energy in the Rsh dim,
                # if slowly --> bull sharks
                # code: generates array of the index for all basking sharks that are
                # on average moving slower than c_l_slower
                #       then applies a randomized multiplier to give them more
                # momentum.  Due to averaging, some may come to a stop until the
                # average matches desired cond
                arr_slow_parts = df_dark_velocities.index[
                    (
                        (
                            df_dark_velocities[list_params_fast].abs().to_numpy()
                            / df_dark_vmax.loc[0, list_params_fast].to_numpy()
                        ).mean(axis=1)
                        < c_l_slow
                    )
                ].to_numpy()
                df_dark_velocities.loc[arr_slow_parts, list_params_fast] = [
                    [
                        df_dark_vmax.loc[0, y]
                        * c_m_vmax
                        * c_m_velocity
                        / 0.5
                        * (-1) ** (bool(random.getrandbits(1)))
                        * np.random.random()
                        for y in list_params_fast
                    ]
                    for _ in arr_slow_parts
                ]

                # Tells each shark where to go
                # code: simply adds the velocity to the current position, updating
                # the position
                df_dark_particles.iloc[:, 1:-3] = (
                    df_dark_velocities.iloc[:, :].to_numpy()
                    + df_dark_particles.iloc[:, 1:-3].to_numpy()
                )
            # Stores all lists that are desired to be saved as dataframes for
            # printing.
            df_dark_gbest_info = df_dark_gbest.copy()
            df_dark_gbest_info[["J01 [A/cm2]", "J02 [A/cm2]"]] = 10 ** (
                -1 * df_dark_gbest_info[["J01 [A/cm2]", "J02 [A/cm2]"]]
            )

            # print results
            ut.myprint(print_file, "------")
            ut.myprint(print_file, "Dark Results")
            ut.myprint(print_file, "GBest = \n", df_dark_gbest.iloc[-1, 1:5].to_string())
            ut.myprint(print_file, "Iteration = ", var_dark_iters)
            ut.myprint(print_file, "Out of ", iter_pso)
            ut.myprint(print_file, "Error = ", df_dark_gbest.iloc[-1, -1])
            ut.myprint(print_file, "------")

            # ----- Second PSO: Diode data -----
            t_diode_time_start = datetime.now()

            # establish how many sharks you want
            var_n_particles = c_particles_per_dim * 3

            # establish which sharks are evaluated and which are bull sharks (fast)
            # and which are basking sharks (slow)
            list_params_active = ["JL [A/cm2]", "J02 [A/cm2]", "n2"]
            list_params_fast = ["J02 [A/cm2]"]
            list_params_slow = ["JL [A/cm2]", "n2"]

            # set up initial guesses; Rs, Rsh, J01, and n1 are based off dark pso
            df_diode_inits = pd.DataFrame(columns=list_params_all)
            df_diode_inits.loc[0] = np.array(
                [
                    var_IV_Jsc,
                    df_dark_gbest.iloc[-1, 1],
                    df_dark_gbest.iloc[-1, 2],
                    df_dark_gbest.iloc[-1, 3],
                    df_dark_gbest.iloc[-1, 4],
                    12,
                    2,
                    1e20,
                ]
            )

            # establish boudaries or size of the ocean.  Rsh: boundary allow eval of
            # guess by slope and guess by dark IV;
            #   J01 and J02 boundaries must match. Both requirements are met by
            # including min and max functions
            df_diode_bounds = pd.DataFrame(
                np.array(
                    [
                        [
                            var_IV_Jsc * (1 - c_JL_perc_init),
                            var_IV_Jsc * (1 + c_JL_perc_init),
                        ],
                        [df_diode_inits.iloc[0, 1], df_diode_inits.iloc[0, 1]],
                        [df_diode_inits.iloc[0, 2], df_diode_inits.iloc[0, 2]],
                        [df_diode_inits.iloc[0, 3], df_diode_inits.iloc[0, 3]],
                        [df_diode_inits.iloc[0, 4], df_diode_inits.iloc[0, 4]],
                        [c_J0_min, c_J0_max],
                        [c_n_min, c_n2_max],
                        [0, 1],
                    ]
                ).T,
                index=["Low", "High"],
                columns=list_params_all,
            )

            # Establish max velocity.  Not needed when boundaries used on sharks,
            # repurposed to ensure movement is maintained
            df_diode_vmax = pd.DataFrame(columns=["JL [A/cm2]", "J02 [A/cm2]", "n2"])
            df_diode_vmax.loc[0] = 0.5 * (
                np.array(
                    [
                        np.diff(df_diode_bounds["JL [A/cm2]"])[0],
                        np.diff(df_diode_bounds["J02 [A/cm2]"])[0],
                        np.diff(df_diode_bounds["n2"])[0],
                    ]
                )
            )

            # this is the school of sharks
            # code: utilizes the triangle random function to generate random sharks
            # with a preference for the initial value
            df_diode_particles = pd.DataFrame(
                np.array(
                    [
                        np.array(
                            [
                                np.random.triangular(
                                    df_diode_bounds.loc["Low", "JL [A/cm2]"],
                                    df_diode_inits.iloc[0, 0],
                                    df_diode_bounds.loc["High", "JL [A/cm2]"],
                                ),
                                df_diode_inits.iloc[0, 1],
                                df_diode_inits.iloc[0, 2],
                                df_diode_inits.iloc[0, 3],
                                df_diode_inits.iloc[0, 4],
                                np.random.triangular(
                                    df_diode_bounds.loc["Low", "J02 [A/cm2]"],
                                    df_diode_inits.iloc[0, 5],
                                    df_diode_bounds.loc["High", "J02 [A/cm2]"],
                                ),
                                np.random.triangular(
                                    df_diode_bounds.loc["Low", "n2"],
                                    df_diode_inits.iloc[0, 6],
                                    df_diode_bounds.loc["High", "n2"],
                                ),
                                1e20,
                            ]
                        )
                        for _ in range(var_n_particles)
                    ]
                ),
                columns=list_params_all,
            )

            # initialize other needed dataframes
            df_diode_pbest = pd.DataFrame(
                np.array([df_diode_inits.iloc[0, :].to_numpy() for _ in range(var_n_particles)]),
                columns=list_params_all,
            )
            df_diode_gbest = pd.DataFrame(np.ones((1, 8)) * 1e100, columns=list_params_all)
            df_diode_velocities = pd.DataFrame(
                np.array([np.zeros((3)) for _ in range(var_n_particles)]),
                columns=["JL [A/cm2]", "J02 [A/cm2]", "n2"],
            )

            # primary for loop which cycles through posiblities to find best values
            iter_gbest = 0
            for iter_pso in range(c_l_total_iter):

                # Checks sharks to make sure that they're in the right area
                for iter_dim in list_params_active:

                    # code: for a given dimension generates array of indexes where
                    # the value is outside the bands for high and low cases
                    arr_high_parts = df_diode_particles.index[
                        (df_diode_particles[iter_dim] >= df_diode_bounds.loc["High", iter_dim])
                    ].to_numpy()
                    arr_low_parts = df_diode_particles.index[
                        (df_diode_particles[iter_dim] <= df_diode_bounds.loc["Low", iter_dim])
                    ].to_numpy()

                    for iter_test_high in arr_high_parts:
                        if (
                            np.mean(
                                np.array(
                                    [
                                        df_diode_pbest.loc[iter_test_high, iter_dim],
                                        df_diode_bounds.loc["High", iter_dim],
                                    ]
                                )
                            )
                            > df_diode_bounds.loc["High", iter_dim]
                        ):
                            df_diode_pbest.loc[iter_test_high, iter_dim] = df_diode_bounds.loc[
                                "High", iter_dim
                            ]
                    for iter_test_low in arr_low_parts:
                        if (
                            np.mean(
                                np.array(
                                    [
                                        df_diode_pbest.loc[iter_test_low, iter_dim],
                                        df_diode_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            )
                            < df_diode_bounds.loc["Low", iter_dim]
                        ):
                            df_diode_pbest.loc[iter_test_low, iter_dim] = df_diode_bounds.loc[
                                "Low", iter_dim
                            ]
                    # code: applys triangular randomizer function to preferentially
                    # return them between the personal best and the boundary they
                    # crossed.
                    df_diode_particles.loc[arr_high_parts, iter_dim] = [
                        np.random.triangular(
                            np.mean(
                                np.array(
                                    [
                                        df_diode_pbest.loc[x, iter_dim],
                                        df_diode_vmax.loc[0, iter_dim]
                                        + df_diode_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            ),
                            np.mean(
                                np.array(
                                    [
                                        df_diode_pbest.loc[x, iter_dim],
                                        df_diode_bounds.loc["High", iter_dim],
                                    ]
                                )
                            ),
                            df_diode_bounds.loc["High", iter_dim],
                        )
                        for x in arr_high_parts
                    ]
                    df_diode_particles.loc[arr_low_parts, iter_dim] = [
                        np.random.triangular(
                            df_diode_bounds.loc["Low", iter_dim],
                            np.mean(
                                np.array(
                                    [
                                        df_diode_pbest.loc[x, iter_dim],
                                        df_diode_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            ),
                            np.mean(
                                np.array(
                                    [
                                        df_diode_pbest.loc[x, iter_dim],
                                        df_diode_vmax.loc[0, iter_dim]
                                        + df_diode_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            ),
                        )
                        for x in arr_low_parts
                    ]
                # Calculates the fit of the shark's current location
                df_diode_particles.loc[:, "RMSE"] = [
                    iaf.double_diode_pso(
                        df_diode_particles.iloc[x, :-1].to_numpy(), df_data_exp_light_iv
                    )
                    for x in range(var_n_particles)
                ]

                # This is the pbest dataframe and stores the best position of each
                # shark
                # code: directly indexes the sharks have moved to more food in both
                # lists and tranferse the info to pbest
                df_diode_pbest.loc[
                    df_diode_particles["RMSE"] < df_diode_pbest["RMSE"], :
                ] = df_diode_particles.loc[df_diode_particles["RMSE"] < df_diode_pbest["RMSE"], :]

                # This loop stores the schools best positions ever.  To  reduce
                # processing time, can be saved as a single vector
                # Currently the df grows and saves updated gbest in new row.  This
                # allows for evaluation of the movement of the group in real time
                # (in spyder)
                if df_diode_gbest.iloc[-1, -1] > np.min(df_diode_particles["RMSE"]):
                    df_diode_gbest.loc[iter_gbest] = df_diode_particles[
                        df_diode_particles["RMSE"] == np.min(df_diode_particles["RMSE"])
                    ].values.tolist()[0]
                    iter_gbest += 1
                    var_diode_iters = iter_pso
                # If target error is reached, time interval is reached, or logic
                # indicates to skip, for loop is cut prematurely
                if (
                    (df_diode_gbest.iloc[-1, -1] < c_target_error)
                    or datetime.now() > t_diode_time_start + timedelta(minutes=c_time_interval / 3)
                    or l_skip_diode
                ):
                    break
                # updating variable which weights the sharks momentum.  Decreases
                # exponentially as interations increase.  This increases the impact
                # of the sharks best position and the schools best position as
                # iterations increase
                var_weight = c_weight_max * c_weight_min ** (-iter_pso)

                # Calculates velocity of each shark combining its current momentum,
                # its best position, and the schools best position
                # code: compares the best postions to the current position arrays and
                # incorporates a randomizer to keep the posibilities high
                df_diode_velocities.iloc[:, :] = (
                    (var_weight * df_diode_velocities.to_numpy())
                    + (2 * np.random.random())
                    * (
                        df_diode_pbest.iloc[:, [0, 5, 6]].to_numpy()
                        - df_diode_particles.iloc[:, [0, 5, 6]].to_numpy()
                    )
                    + (2 * np.random.random())
                    * (
                        df_diode_gbest.iloc[-1, [0, 5, 6]].to_numpy()
                        - df_diode_particles.iloc[:, [0, 5, 6]].to_numpy()
                    )
                )

                # Ensures all particles keep moving, if slowly --> basking sharks
                # code: generates array of the index for all basking sharks that are
                # on average moving slower than c_l_slower then applies a randomized
                # multiplier to give them more momentum.  Due to averaging, some may
                # come to a stop until the average matches desired cond
                arr_slower_parts = df_diode_velocities.index[
                    (
                        df_diode_velocities[list_params_slow].abs().to_numpy()
                        / df_diode_vmax.loc[0, list_params_slow].to_numpy()
                    ).mean(axis=1)
                    < c_l_slower
                ].to_numpy()
                df_diode_velocities.loc[arr_slower_parts, list_params_slow] = [
                    [
                        df_diode_vmax.loc[0, y]
                        * c_m_velocity
                        / 0.5
                        * (-1) ** (bool(random.getrandbits(1)))
                        * np.random.random()
                        for y in list_params_slow
                    ]
                    for _ in arr_slower_parts
                ]

                # code to ensure all particles have a lot of energy in the Rsh dim,
                # if slowly --> bull sharks
                # code: generates array of the index for all basking sharks that are
                # on average moving slower than c_l_slower then applies a randomized
                # multiplier to give them more momentum.  Due to averaging, some may
                # come to a stop until the average matches desired cond
                arr_slow_parts = df_diode_velocities.index[
                    (
                        df_diode_velocities[list_params_fast].abs().to_numpy()
                        / df_diode_vmax.loc[0, list_params_fast].to_numpy()
                    ).mean(axis=1)
                    < c_l_slow
                ].to_numpy()
                df_diode_velocities.loc[arr_slow_parts, list_params_fast] = [
                    [
                        df_diode_vmax.loc[0, y]
                        * c_m_velocity
                        / 0.5
                        * (-1) ** (bool(random.getrandbits(1)))
                        * np.random.random()
                        for y in list_params_fast
                    ]
                    for _ in arr_slow_parts
                ]

                # Tells each shark where to go
                # code: simply adds the velocity to the current position, updating
                # the position
                df_diode_particles.iloc[:, [0, 5, 6]] = (
                    df_diode_velocities.iloc[:, :].to_numpy()
                    + df_diode_particles.iloc[:, [0, 5, 6]].to_numpy()
                )
            # Stores all lists that are desired to be saved as dataframes for
            # printing.
            df_diode_gbest_info = df_diode_gbest.copy()
            df_diode_gbest_info[["J01 [A/cm2]", "J02 [A/cm2]"]] = 10 ** (
                -1 * df_diode_gbest_info[["J01 [A/cm2]", "J02 [A/cm2]"]]
            )

            # print results
            ut.myprint(print_file, "Diode Results")
            ut.myprint(print_file, "GBest = \n", df_diode_gbest.iloc[-1, [0, 5, 6]].to_string())
            ut.myprint(print_file, "Iteration = ", var_diode_iters)
            ut.myprint(print_file, "Out of ", iter_pso)
            ut.myprint(print_file, "Error = ", df_diode_gbest.iloc[-1, -1])
            ut.myprint(print_file, "------")

            #### Third PSO: light data ###

            # establish how many sharks you want
            var_n_particles = c_particles_per_dim * 7

            # establish which sharks are evaluated and which are bull sharks (fast)
            # and which are basking sharks (slow)
            list_params_active = list_params_all[:-1]
            list_params_fast = ["Rsh [ohm-cm2]"]
            list_params_slow = [
                "JL [A/cm2]",
                "Rs [ohm-cm2]",
                "J01 [A/cm2]",
                "n1",
                "J02 [A/cm2]",
                "n2",
            ]

            # set up initial guesses; Rs, Rsh, J01, and n1 are based off dark pso;
            # JL, J02, and n2 are based off diode pso
            df_light_inits = pd.DataFrame(columns=list_params_all)
            df_light_inits.loc[0] = np.array(
                [
                    df_diode_gbest.iloc[-1, 0],
                    df_dark_gbest.iloc[-1, 1],
                    df_dark_gbest.iloc[-1, 2],
                    df_dark_gbest.iloc[-1, 3],
                    df_dark_gbest.iloc[-1, 4],
                    df_diode_gbest.iloc[-1, 5],
                    df_diode_gbest.iloc[-1, 6],
                    1e20,
                ]
            )

            # establish boudaries or size of the ocean.  Rsh: boundary allow eval of
            # guess by slope and guess by dark IV;
            #   J01 and J02 boundaries must match. Both requirements are met by
            # including min and max functions
            df_light_bounds = pd.DataFrame(
                np.array(
                    [
                        [
                            df_light_inits.iloc[0, 0] * (1 - c_JL_perc_init),
                            df_light_inits.iloc[0, 0] * (1 + c_JL_perc_init),
                        ],
                        [
                            df_light_inits.iloc[0, 1] * (1 - c_Rs_perc_init),
                            df_light_inits.iloc[0, 1] * (1 + c_Rs_perc_init),
                        ],
                        [
                            min(
                                [
                                    df_light_inits.iloc[0, 2] * (1 - c_Rsh_perc_init * 0.5),
                                    df_dark_inits.iloc[0, 2] * (1 - c_Rsh_perc_init * 0.5),
                                ]
                            ),
                            max(
                                [
                                    df_light_inits.iloc[0, 2] * (1 + c_Rsh_perc_init * 0.5),
                                    df_dark_inits.iloc[0, 2] * (1 + c_Rsh_perc_init * 0.5),
                                ]
                            ),
                        ],
                        [
                            min(
                                [
                                    df_light_inits.iloc[0, 3] * (1 - c_J0_perc_init * 0.5),
                                    df_light_inits.iloc[0, 5] * (1 - c_J0_perc_init * 0.5),
                                ]
                            ),
                            max(
                                [
                                    df_light_inits.iloc[0, 3] * (1 + c_J0_perc_init * 0.5),
                                    df_light_inits.iloc[0, 5] * (1 + c_J0_perc_init * 0.5),
                                ]
                            ),
                        ],
                        [c_n_min, c_n1_max],
                        [
                            min(
                                [
                                    df_light_inits.iloc[0, 3] * (1 - c_J0_perc_init * 0.5),
                                    df_light_inits.iloc[0, 5] * (1 - c_J0_perc_init * 0.5),
                                ]
                            ),
                            max(
                                [
                                    df_light_inits.iloc[0, 3] * (1 + c_J0_perc_init * 0.5),
                                    df_light_inits.iloc[0, 5] * (1 + c_J0_perc_init * 0.5),
                                ]
                            ),
                        ],
                        [c_n_min, c_n2_max],
                        [0, 1],
                    ]
                ).T,
                index=["Low", "High"],
                columns=list_params_all,
            )

            if l_shunted:
                df_light_bounds.loc["Low", "Rs [ohm-cm2]"] = 1
            # Establish max velocity.  Not needed when boundaries used on sharks,
            # repurposed to ensure movement is maintained
            df_light_vmax = pd.DataFrame(columns=list_params_all[:-1])
            df_light_vmax.loc[0] = 0.5 * (
                np.array(
                    [
                        np.diff(df_light_bounds["JL [A/cm2]"])[0],
                        np.diff(df_light_bounds["Rs [ohm-cm2]"])[0],
                        np.diff(df_light_bounds["Rsh [ohm-cm2]"])[0],
                        np.diff(df_light_bounds["J01 [A/cm2]"])[0],
                        np.diff(df_light_bounds["n1"])[0],
                        np.diff(df_light_bounds["J02 [A/cm2]"])[0],
                        np.diff(df_light_bounds["n2"])[0],
                    ]
                )
            )

            # this is the school of sharks
            # code: utilizes the triangle random function to generate random sharks
            # with a preference for the initial value
            df_light_particles = pd.DataFrame(
                np.array(
                    [
                        np.array(
                            [
                                np.random.triangular(
                                    df_light_bounds.loc["Low", "JL [A/cm2]"],
                                    df_light_inits.iloc[0, 0],
                                    df_light_bounds.loc["High", "JL [A/cm2]"],
                                ),
                                np.random.triangular(
                                    df_light_bounds.loc["Low", "Rs [ohm-cm2]"],
                                    df_light_inits.iloc[0, 1],
                                    df_light_bounds.loc["High", "Rs [ohm-cm2]"],
                                ),
                                np.random.triangular(
                                    df_light_bounds.loc["Low", "Rsh [ohm-cm2]"],
                                    df_light_inits.iloc[0, 2],
                                    df_light_bounds.loc["High", "Rsh [ohm-cm2]"],
                                ),
                                np.random.triangular(
                                    df_light_bounds.loc["Low", "J01 [A/cm2]"],
                                    df_light_inits.iloc[0, 3],
                                    df_light_bounds.loc["High", "J01 [A/cm2]"],
                                ),
                                np.random.triangular(
                                    df_light_bounds.loc["Low", "n1"],
                                    df_light_inits.iloc[0, 4],
                                    df_light_bounds.loc["High", "n1"],
                                ),
                                np.random.triangular(
                                    df_light_bounds.loc["Low", "J02 [A/cm2]"],
                                    df_light_inits.iloc[0, 5],
                                    df_light_bounds.loc["High", "J02 [A/cm2]"],
                                ),
                                np.random.triangular(
                                    df_light_bounds.loc["Low", "n2"],
                                    df_light_inits.iloc[0, 6],
                                    df_light_bounds.loc["High", "n2"],
                                ),
                                1e20,
                            ]
                        )
                        for _ in range(var_n_particles)
                    ]
                ),
                columns=list_params_all,
            )

            # initialize other needed dataframes
            df_light_pbest = pd.DataFrame(
                np.array([df_light_inits.iloc[0, :].to_numpy() for _ in range(var_n_particles)]),
                columns=list_params_all,
            )
            df_light_gbest = pd.DataFrame(np.ones((1, 8)) * 1e100, columns=list_params_all)
            list_plog = []
            df_light_velocities = pd.DataFrame(
                np.array([np.zeros((7)) for _ in range(var_n_particles)]),
                columns=list_params_all[:-1],
            )

            data_fit_volt_real = np.linspace(0, var_IV_Voc + var_IV_Voc * 0.05, 1000)
            data_fit_curr_real_init = np.array(
                [
                    np.interp(
                        x,
                        df_data_exp_light_iv.iloc[:, 0].to_numpy(),
                        df_data_exp_light_iv.iloc[:, 1].to_numpy(),
                    )
                    for x in data_fit_volt_real
                ]
            )

            # primary for loop which cycles through posiblities to find best values
            iter_gbest = 0
            for iter_pso in range(c_l_total_iter):

                # Checks sharks to make sure that they're in the right area
                for iter_dim in list_params_active:

                    # code: for a given dimension generates array of indexes where
                    # the value is outside the bands for high and low cases
                    arr_high_parts = df_light_particles.index[
                        (df_light_particles[iter_dim] >= df_light_bounds.loc["High", iter_dim])
                    ].to_numpy()
                    arr_low_parts = df_light_particles.index[
                        (df_light_particles[iter_dim] <= df_light_bounds.loc["Low", iter_dim])
                    ].to_numpy()

                    for iter_test_high in arr_high_parts:
                        if (
                            np.mean(
                                np.array(
                                    [
                                        df_light_pbest.loc[iter_test_high, iter_dim],
                                        df_light_bounds.loc["High", iter_dim],
                                    ]
                                )
                            )
                            > df_light_bounds.loc["High", iter_dim]
                        ):
                            df_light_pbest.loc[iter_test_high, iter_dim] = df_light_bounds.loc[
                                "High", iter_dim
                            ]
                    for iter_test_low in arr_low_parts:
                        if (
                            np.mean(
                                np.array(
                                    [
                                        df_light_pbest.loc[iter_test_low, iter_dim],
                                        df_light_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            )
                            < df_light_bounds.loc["Low", iter_dim]
                        ):
                            df_light_pbest.loc[iter_test_low, iter_dim] = df_light_bounds.loc[
                                "Low", iter_dim
                            ]
                    # if iter_dim =='JL [A/cm2]':
                    #     if len(arr_high_parts) != 0 or len(arr_low_parts) != 0:
                    #         print('error')

                    # code: applys triangular randomizer function to preferentially
                    # return them between the personal best and the boundary they
                    # crossed.
                    df_light_particles.loc[arr_high_parts, iter_dim] = [
                        np.random.triangular(
                            np.mean(
                                np.array(
                                    [
                                        df_light_pbest.loc[x, iter_dim],
                                        df_light_vmax.loc[0, iter_dim]
                                        + df_light_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            ),
                            np.mean(
                                np.array(
                                    [
                                        df_light_pbest.loc[x, iter_dim],
                                        df_light_bounds.loc["High", iter_dim],
                                    ]
                                )
                            ),
                            df_light_bounds.loc["High", iter_dim],
                        )
                        for x in arr_high_parts
                    ]
                    df_light_particles.loc[arr_low_parts, iter_dim] = [
                        np.random.triangular(
                            df_light_bounds.loc["Low", iter_dim],
                            np.mean(
                                np.array(
                                    [
                                        df_light_pbest.loc[x, iter_dim],
                                        df_light_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            ),
                            np.mean(
                                np.array(
                                    [
                                        df_light_pbest.loc[x, iter_dim],
                                        df_light_vmax.loc[0, iter_dim]
                                        + df_light_bounds.loc["Low", iter_dim],
                                    ]
                                )
                            ),
                        )
                        for x in arr_low_parts
                    ]
                # Calculates the fit of the shark's current location
                df_light_particles.loc[:, "RMSE"] = [
                    iaf.double_diode_pso(
                        df_light_particles.iloc[x, :-1].to_numpy(), df_data_exp_light_iv
                    )
                    for x in range(var_n_particles)
                ]

                # added code to achieve the convention in which n1 is low and n2 is
                # high.  Mathematically irrelevant
                df_light_particles[["J01 [A/cm2]", "n1", "J02 [A/cm2]", "n2"]] = df_light_particles[
                    ["J02 [A/cm2]", "n2", "J01 [A/cm2]", "n1"]
                ].where(
                    df_light_particles["n1"] > df_light_particles["n2"],
                    df_light_particles[["J01 [A/cm2]", "n1", "J02 [A/cm2]", "n2"]].values,
                )

                # this is currently a list of series that stores the improved pbest
                # values.  This is converted to a df and printed to evaluate how well
                # the school of sharks is converging
                # code: extend list with values that meet pbest update requirements
                list_plog.extend(
                    [
                        df_light_particles.loc[x].rename(str(iter_pso) + "-" + str(x))
                        for x in df_light_particles.index[
                            df_light_particles["RMSE"] < df_light_pbest["RMSE"]
                        ]
                    ]
                )

                # This is the pbest dataframe and stores the best position of each
                # shark
                # code: directly indexes the sharks have moved to more food in both
                # lists and tranferse the info to pbest
                df_light_pbest.loc[
                    df_light_particles["RMSE"] < df_light_pbest["RMSE"], :
                ] = df_light_particles.loc[df_light_particles["RMSE"] < df_light_pbest["RMSE"], :]

                # This loop stores the schools best positions ever.  To  reduce
                # processing time, can be saved as a single vector
                # Currently the df grows and saves updated gbest in new row.  This
                # allows for evaluation of the movement of the group in real time
                # (in spyder)
                # This value can also be output for analysis (as apposed to plog) but
                # this is only effective when gbest rapidly updates (like a feeding
                # frenzy) and many values are generated. Personal evaluation tells me
                # that this behavior is prefered as it means that the sharks are
                # schooling around the desired value.

                # This section also plots the output in an updating plot
                if df_light_gbest.iloc[-1, -1] > np.min(df_light_particles["RMSE"]):
                    # code: when the smallest 'RMSE' in school is better than gbest,
                    # it directly stores it into new row.  Additional counters input
                    # to provide info
                    df_light_gbest.loc[iter_gbest] = df_light_particles[
                        df_light_particles["RMSE"] == np.min(df_light_particles["RMSE"])
                    ].values.tolist()[0]
                    iter_gbest += 1
                    var_light_iters = iter_pso

                    # generate profile based on fit params for comparison
                    data_fit_curr_real = np.array(
                        [
                            optimize.fsolve(
                                iaf.double_diode_cost,
                                data_fit_curr_real_init[x],
                                (
                                    data_fit_volt_real[x],
                                    df_light_gbest.iloc[-1, :-1].to_numpy(),
                                ),
                                xtol=1e-12,
                            )[0]
                            for x in range(len(data_fit_volt_real))
                        ]
                    )

                    # establish graph limits for better plots
                    if df_light_gbest.iloc[-1, 0] > 1:
                        graphlim = 10
                    else:
                        if round(df_light_gbest.iloc[-1, 0], 2) < df_light_gbest.iloc[-1, 0]:
                            graphlim = round(df_light_gbest.iloc[-1, 0], 2) + 0.005
                        else:
                            graphlim = round(df_light_gbest.iloc[-1, 0], 2)
                    # Plots results to file which updates.When viewed in file
                    # explorer with viewing pane, you can see results in real time
                    plt.figure(1)
                    plt.plot(
                        df_data_exp_light_iv.iloc[:, 0],
                        df_data_exp_light_iv.iloc[:, 1],
                        "o",
                        data_fit_volt_real,
                        data_fit_curr_real,
                        "--",
                    )
                    plt.grid()
                    plt.xlim(left=0, right=0.75)
                    plt.ylim(bottom=0, top=graphlim)
                    plt.xlabel("Voltage [V]")
                    plt.ylabel("Current Density [A/cm2]")
                    plt.text(0.01, 0.008, r"$R_{S}$: %.2f" % df_light_gbest.iloc[-1, 1])
                    plt.text(0.01, 0.006, r"$R_{Sh}$: %.2f" % df_light_gbest.iloc[-1, 2])
                    plt.text(0.01, 0.003, "Iteration: %.0f" % iter_pso)
                    plt.text(0.01, 0.001, "Err: %.2e" % df_light_gbest.iloc[-1, 7])
                    plt.text(0.01, 0.011, "Jsc: %.2e" % df_light_gbest.iloc[-1, 0])
                    plt.title(name)
                    newpath = os.sep.join((dirpath, "Plot_Current.png"))
                    plt.savefig(newpath)
                    plt.close("all")
                # if df_light_gbest.iloc[-1,-1]
                # If target error is reached or time interval is reached, for loop is
                # cut prematurely
                if (
                    df_light_gbest.iloc[-1, -1] < c_target_error
                ) or datetime.now() > t_run_time_start + timedelta(minutes=c_time_interval):
                    break
                # updating variable which weights the sharks momentum.  Decreases
                # exponentially as interations increase.  This increases the impact
                # of the sharks best position and the schools best position as
                # iterations increase
                var_weight = c_weight_max * c_weight_min ** (-iter_pso)

                # Calculates velocity of each shark combining its current momentum,
                # its best position, and the schools best position
                # code: compares the best postions to the current position arrays and
                # incorporates a randomizer to keep the posibilities high
                df_light_velocities.iloc[:, :] = (
                    (var_weight * df_light_velocities.to_numpy())
                    + (2 * np.random.random())
                    * (
                        df_light_pbest.iloc[:, :-1].to_numpy()
                        - df_light_particles.iloc[:, :-1].to_numpy()
                    )
                    + (2 * np.random.random())
                    * (
                        df_light_gbest.iloc[-1, :-1].to_numpy()
                        - df_light_particles.iloc[:, :-1].to_numpy()
                    )
                )

                # Ensures all particles keep moving, if slowly --> basking sharks
                # code: generates array of the index for all basking sharks that are
                # on average moving slower than c_l_slower
                #       then applies a randomized multiplier to give them more
                # momentum.  Due to averaging, some may come to a stop until the
                # average matches desired cond
                arr_slower_parts = df_light_velocities.index[
                    (
                        df_light_velocities[list_params_slow].abs().to_numpy()
                        / df_light_vmax.loc[0, list_params_slow].to_numpy()
                    ).mean(axis=1)
                    < c_l_slower
                ].to_numpy()
                df_light_velocities.loc[arr_slower_parts, list_params_slow] = [
                    [
                        df_light_vmax.loc[0, y]
                        * c_m_velocity
                        / 0.5
                        * (-1) ** (bool(random.getrandbits(1)))
                        * np.random.random()
                        for y in list_params_slow
                    ]
                    for _ in arr_slower_parts
                ]

                # code to ensure all particles have a lot of energy in the Rsh dim,
                # if slowly --> bull sharks
                # code: generates array of the index for all basking sharks that are
                # on average moving slower than c_l_slower then applies a randomized
                # multiplier to give them more momentum.  Due to averaging, some may
                # come to a stop until the average matches desired cond
                arr_slow_parts = df_light_velocities.index[
                    (
                        df_light_velocities[list_params_fast].abs().to_numpy()
                        / df_light_vmax.loc[0, list_params_fast].to_numpy()
                    ).mean(axis=1)
                    < c_l_slow
                ].to_numpy()
                df_light_velocities.loc[arr_slow_parts, list_params_fast] = [
                    [
                        df_light_vmax.loc[0, y]
                        * c_m_vmax
                        * c_m_velocity
                        / 0.5
                        * (-1) ** (bool(random.getrandbits(1)))
                        * np.random.random()
                        for y in list_params_fast
                    ]
                    for _ in arr_slow_parts
                ]

                # Tells each shark where to go
                # code: simply adds the velocity to the current position, updating
                # the position
                df_light_particles.iloc[:, :-1] = (
                    df_light_velocities.iloc[:, :].to_numpy()
                    + df_light_particles.iloc[:, :-1].to_numpy()
                )

                # code to remeber previous PSO results.  Only impacts 1 particle. -->
                # The grey bamboo shark (it has amazing memory)
                df_light_particles.iloc[0, :-1] = (
                    df_light_particles.iloc[0, :-1].to_numpy()
                    + df_light_inits.iloc[0, :-1].to_numpy()
                ) / 2

                # velocity of bull sharks can be too high, this forces partcle 0 to
                # be all grey bamboo sharks and not move to far away from where we
                # want them
                # code: probably could be better optemized
                if (
                    abs(
                        round((1 - df_light_particles.iloc[0, 2] / df_light_inits.iloc[0, 2]) * 100)
                    )
                    > 10
                ):
                    df_light_particles.iloc[0, 2] = df_light_inits.iloc[0, 2]
            # Stores all lists that are desired to be saved as dataframes for
            # printing.  Plog limited to 1000 lines
            df_light_gbest_info = df_light_gbest.copy()
            df_light_gbest_info[["J01 [A/cm2]", "J02 [A/cm2]"]] = 10 ** (
                -1 * df_light_gbest_info[["J01 [A/cm2]", "J02 [A/cm2]"]]
            )
            df_plog = pd.DataFrame(list_plog[-1000:])

            # print results
            ut.myprint(print_file, "Light Results")
            ut.myprint(print_file, "Gbest = \n", df_light_gbest_info.iloc[-1, :-1].to_string())
            ut.myprint(print_file, "On Iteration ", var_light_iters)
            ut.myprint(print_file, "Out of ", iter_pso)
            ut.myprint(print_file, "Error = ", df_light_gbest.iloc[-1, -1])
            ut.myprint(print_file, "------")
            ut.myprint(print_file, "")

            # ----- Conclusitory code to save results -----

            if round(df_light_gbest.iloc[-1, 0], 2) < df_light_gbest.iloc[-1, 0]:
                graphlim = round(df_light_gbest.iloc[-1, 0], 2) + 0.005
            else:
                graphlim = round(df_light_gbest.iloc[-1, 0], 2)
            # Generate fit profile from best fit parameters
            data_fit_curr_real = np.array(
                [
                    optimize.fsolve(
                        iaf.double_diode_cost,
                        data_fit_curr_real_init[x],
                        (
                            data_fit_volt_real[x],
                            df_light_gbest.iloc[-1, :-1].to_numpy(),
                        ),
                        xtol=1e-12,
                    )[0]
                    for x in range(len(data_fit_volt_real))
                ]
            )

            res_array = np.append(
                res_p0, np.array(ut.cell_params(data_fit_volt_real, data_fit_curr_real))
            )

            res_array = np.append(
                res_array,
                [
                    df_light_gbest.iloc[-1, 1],
                    var_Rsh_slope,
                    df_dark_gbest_info.iloc[-1, 2],
                ],
            )
            res_array = np.append(res_array, df_light_gbest_info.iloc[-1, 2:])

            # Save best fit plot
            plt.figure(2)
            plt.plot(
                df_data_exp_light_iv.iloc[:, 0],
                df_data_exp_light_iv.iloc[:, 1],
                "o",
                data_fit_volt_real,
                data_fit_curr_real,
                "--",
            )
            plt.grid()
            plt.xlim(left=0, right=0.75)
            plt.ylim(bottom=0, top=graphlim)
            plt.xlabel("Voltage [V]")
            plt.ylabel("Current Density [A/cm2]")
            plt.text(0.01, 0.008, r"$R_{S}$: %.2f" % df_light_gbest.iloc[-1, 1])
            plt.text(0.01, 0.006, r"$R_{Sh}$: %.2f" % df_light_gbest.iloc[-1, 2])
            plt.text(0.01, 0.003, "Iteration: %.0f" % iter_pso)
            plt.text(0.01, 0.001, "Err: %.2e" % df_light_gbest.iloc[-1, 7])
            plt.text(0.01, 0.011, "Jsc: %.2e" % df_light_gbest.iloc[-1, 0])
            plt.title(name)
            newpath = os.sep.join((dirpath, f"{name}.png"))
            plt.savefig(newpath)
            plt.close("all")

            # Finalize result array
            res_frame = pd.DataFrame([res_array.tolist()], columns=Result_cols)

            res_frame["Date-Time"] = pd.to_datetime(res_frame["Date-Time"], yearfirst=True)
            res_frame[Result_cols[1:]] = res_frame[Result_cols[1:]].astype(float)

            if l_check == 1 and df_light_gbest.iloc[-1, 7] > prev_results.iloc[indexer, -1]:
                res_compiled.loc[name, Result_cols] = prev_results.loc[name].to_numpy(copy=True)
            else:
                res_compiled.loc[name, Result_cols] = res_frame.to_numpy(copy=True)[0]
        # Save result array to temp file so that each result is saved (in case of
        # error)
        # without disrupting the main result file
        res_compiled.to_excel(os.sep.join((mypath, "Result_log_temp.xlsx")))

        if save_gbest:
            df_plog.to_excel(os.sep.join((dirpath, f"{name}.xlsx")))

    outlog = "".join(("Result_log_", folderstodo[myfolders.index(mypath)], ".xlsx"))
    outfinal = "".join(("Result_final_", folderstodo[myfolders.index(mypath)], ".xlsx"))

    # Save final results and remove temp file
    res_compiled.to_excel(os.sep.join((mypath, outlog)))
    os.remove(os.sep.join((mypath, "Result_log_temp.xlsx")))

    if 0:
        iaf.iv_stats_dd(mypath, outlog, outfinal)
