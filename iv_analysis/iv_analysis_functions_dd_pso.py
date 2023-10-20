"""
Created on Thu Aug 13 08:54:41 2020.
Calculate the output of a commercial solar module.
Currently only considers the emitter so that the metalization
losses are ignored.
@author: j2cle.
"""
import os
import numpy as np
import pandas as pd
import utilities as ut

from scipy import optimize
from statsmodels.stats.weightstats import DescrStatsW

np.seterr(divide="ignore", invalid="ignore")


# %% Functions
# def Idiode_fsolver(J, V, params, temp=298.15):
#     """test"""
#     # equation constants
#     k = ut.K_B__EV
#     vt = params[2] * k * temp
#     kt = params[4] * k * temp

#     # return total diode current
#     return (
#         params[0]
#         - params[1] * (np.exp((V + params[5] * J) / vt) - 1)
#         - params[3] * (np.exp((V + params[5] * J) / kt) - 1)
#         - (V + params[5] * J) / params[6]
#         - J
#     )


def double_diode_cost(J, V, params, temp=298.15):
    """test"""
    # equation constants
    k = ut.K_B__EV
    vt = params[4] * k * temp
    kt = params[6] * k * temp

    j01 = 10 ** (-1 * params[3])
    j02 = 10 ** (-1 * params[5])

    if J > 200:
        J = 200

    if params[5] == 0:
        j02 = 0
        kt = vt

    if params[0] == 0:
        curr = (
            j01 * (np.exp((V - params[1] * J) / vt) - 1)
            + j02 * (np.exp((V - params[1] * J) / kt) - 1)
            + (V - params[1] * J) / params[2]
            - J
        )
    else:
        curr = (
            params[0]
            - j01 * (np.exp((V + params[1] * J) / vt) - 1)
            - j02 * (np.exp((V + params[1] * J) / kt) - 1)
            - (V + params[1] * J) / params[2]
            - J
        )

    # return total diode current
    return curr


# def IdiodeComplexDD_PSO(params, diode_data, temp=298.15):
#     """test"""

#     current_new = np.ones_like(diode_data.iloc[:, 1].values)
#     for i in range(len(current_new)):
#         current_new[i] = optimize.fsolve(
#             Idiode_fsolver, diode_data.iloc[i, 1], (diode_data.iloc[i, 0], params), xtol=1e-12
#         )[0]

#     fit_final = pd.DataFrame([diode_data.iloc[:, 0].values, current_new]).T

#     return np.sqrt(
#         np.mean(abs(diode_data.iloc[:, 1].values - fit_final.iloc[:, 1].values) ** 2)
#     )  # +


def double_diode_pso(params, diode_data, temp=298.15):
    """test"""

    current_new = np.ones_like(diode_data.iloc[:, 1].values)
    for i in range(len(current_new)):
        current_new[i] = optimize.fsolve(
            double_diode_cost, diode_data.iloc[i, 1], (diode_data.iloc[i, 0], params), xtol=1e-12
        )[0]

    fit_final = pd.DataFrame([diode_data.iloc[:, 0].values, current_new]).T

    return np.sqrt(np.mean(abs(diode_data.iloc[:, 1].values - fit_final.iloc[:, 1].values) ** 2))


# def to_excel_sheet(dataframes, path, name, sheet):
#     with pd.ExcelWriter(os.sep.join((path, f"{name}.xlsx")), engine="xlsxwriter") as writer:
#         workbook = writer.book
#         worksheet = workbook.add_worksheet(sheet)
#         writer.sheets[sheet] = worksheet

#         COLUMN = 0
#         row = 0

#         for df in dataframes:
#             worksheet.write_string(row, COLUMN, df.name)
#             row += 1
#             df.to_excel(writer, sheet_name=sheet, startrow=row, startcol=COLUMN)
#             COLUMN += df.shape[1] + 1
#             row = 0


def compiler(mypath):
    np.seterr(divide="ignore", invalid="ignore")

    for (dirpath, dirnames, filenames) in os.walk(mypath):
        break

    filepaths = mypath

    # import all files in a folder
    files = []
    IV_files = []
    i = 0
    for filename in os.listdir(filepaths[:]):
        if filename.endswith("jvtst"):
            files.insert(i, os.path.join(str(filepaths[:]), str(filename)))
            IV_files.insert(i, str(filename))
            i += 1

    writer = pd.ExcelWriter(os.sep.join((mypath, "Compiled.xlsx")), engine="openpyxl")

    for indexer in range(0, len(files)):
        # for indexer in test_index:

        IV_Data_Raw = pd.read_csv(files[indexer], sep="\t", header=31, encoding="mbcs")
        IV_Base_Info_Raw = pd.read_csv(
            files[indexer], sep="\t", header=None, index_col=0, nrows=12, encoding="mbcs"
        )
        IV_Base_Info_Raw.name = "Base_Info"
        IV_Elec_Info_Raw = pd.read_csv(
            files[indexer],
            index_col=0,
            header=None,
            sep="\t",
            skiprows=13,
            nrows=8,
            encoding="mbcs",
        )
        IV_Elec_Info_Raw.name = "Elec_Info"
        name = IV_files[indexer][15:-6]

        IV_Data_Raw["Light Up J(A/sqcm)"] = IV_Data_Raw["Light Up J(A/sqcm)"].values  # * -1
        IV_Data_Raw["Dark Up J(A/sqcm)"] = IV_Data_Raw["Dark Up J(A/sqcm)"].values  # * -1

        IV_Data_Raw["Light Down V(Volts)"] = IV_Data_Raw["Light Down V(Volts)"].values[::-1]
        IV_Data_Raw["Light Down J(A/sqcm)"] = IV_Data_Raw["Light Down J(A/sqcm)"].values[
            ::-1
        ]  # * -1
        IV_Data_Raw["Dark Down V(Volts)"] = IV_Data_Raw["Dark Down V(Volts)"].values[::-1]
        IV_Data_Raw["Dark Down J(A/sqcm)"] = IV_Data_Raw["Dark Down J(A/sqcm)"].values[::-1]  # * -1

        IV_Data_Raw["Dark Down V(Volts)"] = IV_Data_Raw["Dark Down V(Volts)"].shift(-1)
        IV_Data_Raw["Dark Down J(A/sqcm)"] = IV_Data_Raw["Dark Down J(A/sqcm)"].shift(-1)

        Light_Up = pd.DataFrame(
            IV_Data_Raw.iloc[:, 1].dropna().values,
            index=IV_Data_Raw.iloc[:, 0].dropna().values,
            columns=["J(A/sqcm)"],
        )
        Light_Up.name = "Light_Up"
        Light_Up.index.name = "Volt (V)"
        Light_Down = pd.DataFrame(
            IV_Data_Raw.iloc[:, 3].dropna().values,
            index=IV_Data_Raw.iloc[:, 2].dropna().values,
            columns=["J(A/sqcm)"],
        )
        Light_Down.name = "Light_Down"
        Light_Down.index.name = "Volt (V)"

        Dark_Up = pd.DataFrame(
            IV_Data_Raw.iloc[:, 5].dropna().values,
            index=IV_Data_Raw.iloc[:, 4].dropna().values,
            columns=["J(A/sqcm)"],
        )
        Dark_Up.name = "Dark_Up"
        Dark_Up.index.name = "Volt (V)"
        Dark_Down = pd.DataFrame(
            IV_Data_Raw.iloc[:, 7].dropna().values,
            index=IV_Data_Raw.iloc[:, 6].dropna().values,
            columns=["J(A/sqcm)"],
        )
        Dark_Down.name = "Dark_Down"
        Dark_Down.index.name = "Volt (V)"

        up_write = (Light_Up, Dark_Up, IV_Base_Info_Raw, IV_Elec_Info_Raw)
        down_write = (Light_Down, Dark_Down, IV_Base_Info_Raw, IV_Elec_Info_Raw)

        workbook = writer.book

        COLUMN = 0
        ROW = 1

        for df in up_write:
            # worksheet.write_string(row, COLUMN, df.name)
            df.to_excel(writer, sheet_name=name + " up", startrow=ROW, startcol=COLUMN)
            worksheet = workbook.get_sheet_by_name(name + " up")
            COLUMN += 1
            cellref = worksheet.cell(row=ROW, column=COLUMN)
            cellref.value = df.name
            # worksheet = workbook.worksheets[0]
            COLUMN += df.shape[1]
            # row = 0

        COLUMN = 0
        ROW = 1

        for df in down_write:
            df.to_excel(writer, sheet_name=name + " down", startrow=ROW, startcol=COLUMN)
            worksheet = workbook.get_sheet_by_name(name + " down")
            COLUMN += 1
            cellref = worksheet.cell(row=ROW, column=COLUMN)
            cellref.value = df.name
            # worksheet = workbook.worksheets[0]
            COLUMN += df.shape[1]
            # row = 0

    writer.save()

    return


def iv_stats_dd(mypath, infile, outfile):
    final_cols = [
        "Date-Time",
        "Voc [V]",
        "Voc std [V]",
        "Jsc [A/cm2]",
        "Jsc std [A/cm2]",
        "FF [%]",
        "FF std [%]",
        "Vmp [V]",
        "Vmp std [V]",
        "Jmp [A/cm2]",
        "Jmp std [A/cm2]",
        "Pmp [W/cm2]",
        "Pmp std [W/cm2]",
        "Rs [ohm-cm2]",
        "Rs std[ohm-cm2]",
        "Rsh (slope)[ohm-cm2]",
        "Rsh (slope) std [ohm-cm2]",
        "Rsh (dark)[ohm-cm2]",
        "Rsh (dark) std [ohm-cm2]",
        "Rsh (light)[ohm-cm2]",
        "Rsh (light) std [ohm-cm2]",
        "J01 [A/cm2]",
        "J01 std [A/cm2]",
        "n1",
        "n1 std",
        "J02 [A/cm2]",
        "J02 std [A/cm2]",
        "n2",
        "n2 std",
        "RMSE",
        "RMSE std",
    ]

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

    prev_results = pd.read_excel(os.sep.join((mypath, infile)), index_col=0)

    prev_results["Date-Time"] = pd.to_datetime(prev_results["Date-Time"], yearfirst=True)
    prev_results[Result_cols[1:]] = prev_results[Result_cols[1:]].astype(float)

    all_runs = prev_results.index.values
    each_set = np.zeros_like(all_runs)

    for i in range(len(all_runs)):
        space = all_runs[i].find(" ")
        each_set[i] = all_runs[i][0 : space - 2]

    slow = 0

    for fast in range(len(each_set)):
        if each_set[fast] != each_set[slow]:
            slow += 1
            each_set[slow] = each_set[fast]

    each_set = each_set[0 : slow + 1]

    mean_res = pd.DataFrame(index=each_set, columns=final_cols)

    for j in range(len(each_set)):
        Voc_set = []
        Jsc_set = []
        FF_set = []
        Vmp_set = []
        Jmp_set = []
        Pmp_set = []
        Rsd_set = []
        Rshs_set = []
        Rshd_set = []
        Rshdd_set = []
        J01_set = []
        n1_set = []
        J02_set = []
        n2_set = []
        err_set = []

        for i in range(len(all_runs)):
            if (
                each_set[j] in all_runs[i]
                and all_runs[i][len(each_set[j]) : len(each_set[j]) + 1] == "-"
            ):
                Voc_set = np.append(Voc_set, prev_results.loc[all_runs[i], "Voc [V]"])
                Jsc_set = np.append(Jsc_set, prev_results.loc[all_runs[i], "Jsc [A/cm2]"])
                FF_set = np.append(FF_set, prev_results.loc[all_runs[i], "FF [%]"])
                Vmp_set = np.append(Vmp_set, prev_results.loc[all_runs[i], "Vmp [V]"])
                Jmp_set = np.append(Jmp_set, prev_results.loc[all_runs[i], "Jmp [A/cm2]"])
                Pmp_set = np.append(Pmp_set, prev_results.loc[all_runs[i], "Pmp [W/cm2]"])
                Rsd_set = np.append(Rsd_set, prev_results.loc[all_runs[i], "Rs [ohm-cm2]"])

                Rshs_set = np.append(
                    Rshs_set, prev_results.loc[all_runs[i], "Rsh (slope)[ohm-cm2]"]
                )
                Rshd_set = np.append(Rshd_set, prev_results.loc[all_runs[i], "Rsh (dark)[ohm-cm2]"])
                Rshdd_set = np.append(
                    Rshdd_set, prev_results.loc[all_runs[i], "Rsh (light)[ohm-cm2]"]
                )

                J01_set = np.append(J01_set, prev_results.loc[all_runs[i], "J01 [A/cm2]"])
                n1_set = np.append(n1_set, prev_results.loc[all_runs[i], "n1"])
                J02_set = np.append(J02_set, prev_results.loc[all_runs[i], "J02 [A/cm2]"])
                n2_set = np.append(n2_set, prev_results.loc[all_runs[i], "n2"])

                err_set = np.append(err_set, prev_results.loc[all_runs[i], "RMSE"])

                date = prev_results.loc[all_runs[i], "Date-Time"]

        err_stats = DescrStatsW(err_set, ddof=0)

        # err_set = np.ones_like(Voc_set)
        err_set = (1 / np.array(err_set)) / np.max(1 / np.array(err_set))

        Voc_stats = DescrStatsW(Voc_set, weights=err_set, ddof=0)
        Jsc_stats = DescrStatsW(Jsc_set, weights=err_set, ddof=0)
        FF_stats = DescrStatsW(FF_set, weights=err_set, ddof=0)
        Vmp_stats = DescrStatsW(Vmp_set, weights=err_set, ddof=0)
        Jmp_stats = DescrStatsW(Jmp_set, weights=err_set, ddof=0)
        Pmp_stats = DescrStatsW(Pmp_set, weights=err_set, ddof=0)
        Rsd_stats = DescrStatsW(Rsd_set, weights=err_set, ddof=0)

        Rshs_stats = DescrStatsW(Rshs_set, weights=err_set, ddof=0)
        Rshd_stats = DescrStatsW(Rshd_set, weights=err_set, ddof=0)
        Rshdd_stats = DescrStatsW(Rshdd_set, weights=err_set, ddof=0)

        J01_stats = DescrStatsW(J01_set, weights=err_set, ddof=0)
        n1_stats = DescrStatsW(n1_set, weights=err_set, ddof=0)
        J02_stats = DescrStatsW(J02_set, weights=err_set, ddof=0)
        n2_stats = DescrStatsW(n2_set, weights=err_set, ddof=0)

        Rshd_stats = DescrStatsW(Rshd_set, weights=err_set, ddof=0)

        res_array = np.array(
            [
                date,
                Voc_stats.mean,
                Voc_stats.std,
                Jsc_stats.mean,
                Jsc_stats.std,
                FF_stats.mean,
                FF_stats.std,
                Vmp_stats.mean,
                Vmp_stats.std,
                Jmp_stats.mean,
                Jmp_stats.std,
                Pmp_stats.mean,
                Pmp_stats.std,
                Rsd_stats.mean,
                Rsd_stats.std,
                Rshs_stats.mean,
                Rshs_stats.std,
                Rshd_stats.mean,
                Rshd_stats.std,
                Rshdd_stats.mean,
                Rshdd_stats.std,
                J01_stats.mean,
                J01_stats.std,
                n1_stats.mean,
                n1_stats.std,
                J02_stats.mean,
                J02_stats.std,
                n2_stats.mean,
                n2_stats.std,
                err_stats.mean,
                err_stats.std,
            ]
        )
        mean_res.loc[each_set[j], final_cols] = res_array

    mean_res["Date-Time"] = pd.to_datetime(mean_res["Date-Time"], yearfirst=True)
    mean_res[final_cols[1:]] = mean_res[final_cols[1:]].astype(float)

    mean_res.to_excel(os.sep.join((mypath, outfile)))
    return
