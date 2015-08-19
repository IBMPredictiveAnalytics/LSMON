# -*- coding: UTF-8 -*-

#********************************************************************************.
#* Title/Objective: Output lsmon.exe license usage details in an SPSS pivot table.
#* Context/Project: SPSS General.
#* Description: Gives an overview of the number of licenses in use, for each SPSS feature.
#* Author: Albert-Jan Roskam.
#* Maintainer: Albert-Jan Roskam.
#* Last saved (yyyy-mm-dd @ hh:mm:ss): 2014-05-09 @ 10:55:59.
#* SPSS & OS version: 20.0.0.2 on Windows 7.
#********************************************************************************.

__version__ = "1.0.2"
__author__ = "Albert-Jan Roskam"

import os, subprocess, re, time, sys
import spssaux, spss
from extension import Template, Syntax, processcmd

feature_codes = {\
      1200: 'IBM SPSS Statistics',
      1201: 'Tables Original',
      1202: 'IBM SPSS Regression',
      1203: 'IBM SPSS Advanced Statistics',
      1204: 'Trends Original',
      1205: 'IBM SPSS Exact Tests',
      1206: 'IBM SPSS Categories',
      1207: 'IBM SPSS Missing Values',
      1208: 'IBM SPSS Conjoint',
      1210: 'IBM SPSS Custom Tables',
      1211: 'IBM SPSS Complex Samples',
      1212: 'IBM SPSS Decision Trees',
      1213: 'IBM SPSS Data Preparation',
      1214: 'IBM SPSS Programmability',
      1215: 'IBM SPSS Advanced Visualization',
      1216: 'IBM SPSS Forecasting',
      1217: 'IBM SPSS Adapter',
      1218: 'IBM SPSS Neural Networks',
      1219: 'IBM SPSS Direct Marketing',
      1220: 'IBM SPSS Bootstrapping',
      1221: 'IBM SPSS Statistics Base',
      8400: 'Clementine Client Windows All languages'}

def issue_warning(msg):
    """Issue a warning that is displayed in an SPSS pivot table"""
    spss.StartProcedure("Warning!")
    table = spss.BasePivotTable("Warnings ", "Warnings")
    table.Append(spss.Dimension.Place.row,"rowdim", hideLabels=True)
    rowLabel = spss.CellText.String("1")
    table[(rowLabel,)] = spss.CellText.String(msg)
    spss.EndProcedure()
    
def get_hostname(lines):
    m = re.search('\[Contacting .* host "(.*)".*\]', "\n".join(lines))
    if m:
        hostname = m.group(1)
        if hostname.lower() == "no-net":
            msg = "This program is intended for concurrent licenses only"
            issue_warning(msg)
            spss.Submit("show license.")
        return hostname
    else:
        raise ValueError("Hostname not found")

def lsmon_():
    """Call lsmon.exe in the SPSS installation directory and return feature numbers, 
    used unreserved licenses, used reserved licenses, total number of licenses,
    total number of reserved licenses, total number of unreserved licenses,
    license server"""
    extension = ".exe" if sys.platform.startswith("win") else ""
    lsmon_exe = os.path.join(spssaux.GetSPSSInstallDir(), "lsmon%s" % extension)
    proc = subprocess.Popen(lsmon_exe, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    lines = proc.communicate()[0].split("\n")
    items = ["Feature name", "Maximum concurrent user", "reserved tokens in use", "Available reserved"]
    pattern = re.compile("("+ "|".join(items) + ")", re.I)
    tokens = [int(re.search('\d+', r).group(0)) for r in lines if 
                   pattern.search(r) and not r.startswith("     ")]
    features = tokens[0::5]
    maxes = tokens[1::5]
    unreserveds = tokens[2::5]
    reserveds = tokens[3::5]
    available_reserveds = tokens[4::5]
    total_reserveds = [used_res + avail_res for used_res, avail_res in zip(reserveds, available_reserveds)]
    total_unreserveds = [max_ - total_res for max_, total_res in zip(maxes, total_reserveds)]
    hostname = get_hostname(lines)
    return features, unreserveds, reserveds, maxes, total_reserveds, total_unreserveds, hostname

def lsmon():
    """Create an SPSS pivot table of the license usage data returned by function lsmon_"""
    features, unreserveds, reserveds, maxes, total_reserveds, total_unreserveds, hostname = lsmon_()
    feature_labels = [feature_codes.get(f, "(Unknown)") for f in features]
    asStr = spss.CellText.String
    asInt = lambda value, fmt=spss.FormatSpec.Count: spss.CellText.Number(value, fmt)
    percentSpecs = [spss.FormatSpec.Percent] * len(features)
    try:
        stamp = time.strftime("%Y-%m-%d at %H:%M:%M")
        spss.StartProcedure("SPSS license usage (%s)" % stamp)
        table = spss.BasePivotTable("Table", "lsmon")
        row = table.Append(spss.Dimension.Place.row,"feature #")
        column = table.Append(spss.Dimension.Place.column,"Usage")

        for feature in features:
            table.SetCategories(row, asStr(feature))
        table.SetCellsByColumn(asStr("label"), map(asStr, feature_labels))

        table.SetCellsByColumn(asStr("unreserved\nn"), map(asInt, unreserveds))
        percents = [unreserveds[i] / float(total_unres + 10e-10) * 100 for 
                    i, total_unres in enumerate(total_unreserveds)]
        table.SetCellsByColumn(asStr("unreserved\n%"), map(asInt, percents, percentSpecs))

        table.SetCellsByColumn(asStr("reserved\nn"), map(asInt, reserveds))
        percents = [reserveds[i] / float(total_res + 10e-10) * 100 for 
                    i, total_res in enumerate(total_reserveds)]
        table.SetCellsByColumn(asStr("reserved\n%"), map(asInt, percents, percentSpecs))

        totals = [unreserved + reserved for unreserved, reserved in zip(unreserveds, reserveds)]
        table.SetCellsByColumn(asStr("total\nn"), map(asInt, totals))
        percents = [(unreserveds[i] + reserveds[i]) / float(max_ + 10e-10) * 100 for 
                    i, max_ in enumerate(maxes)]
        table.SetCellsByColumn(asStr("total\n%"), map(asInt, percents, percentSpecs))

        table.SetCellsByColumn(asStr("maximum\nn"), map(asInt, maxes))
        table.Caption("License server: %s." % hostname)
    finally:
        spss.EndProcedure()


def setUp():
    spss.Submit(["preserve.", "set printback = none."])

def doFormat():
    """format features of which (almost) all licenses are in use."""
    try:
        import SPSSINC_MODIFY_TABLES
        modify_tables_ok = True
    except ImportError:
        modify_tables_ok = False
    cmds = ("_sync.\n"
            "spssinc modify tables\n"
            "  subtype='lsmon' select=2 4 6 dimension=columns level=-1 process=preceding\n"
            "  /styles applyto='x >= 95' textcolor=255 0 0.\n"
            "_sync.\n"
            "spssinc modify tables\n"
            "  subtype='lsmon' select=2 4 6 dimension=columns level=-1 process=preceding\n"
            "  /styles applyto='x >= 100' textcolor=255 0 0 backgroundcolor=255 255 0.\n")
    if modify_tables_ok:    
        spss.Submit(cmds)

def tearDown():
    spss.Submit("restore.")


helptext = r"""LSMON [/HELP].

LSMON -  Monitor concurrent license usage (as returned by lsmon.exe). Gives number and proportion
of SPSS licenses used, by feature and by reserved/unreserved license type. This assumes
that the caller has a concurrent license, and that the LSHOST environment variable points
to the license server

/HELP prints this help and does nothing else.
"""

def Run(args):
    """Execute the LSMON command"""
    try:
        setUp()

        args = args[args.keys()[0]]
        #print args   #debug
        oobj = Syntax([Template("HELP", subc="", ktype="bool")])

        # A HELP subcommand overrides all else
        if args.has_key("HELP"):
            print helptext
        else:
            processcmd(oobj, args, lsmon)
        doFormat()
    finally:
        tearDown()
