#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lector_scheduling.py: Creates a schedule for lectors in masses.

Copyright 2022, Carlos Eduardo de Andrade <ce.andrade@gmail.com>

Usage:
  lector_scheduling.py -l <lectors_list> -d <dates_list> -r <readings_list> \
-o <output_file>

Arguments:
  -l --lectors_list <arg>  A text file with names and blocked dates.
        One each line, we have the person's name followed comma-separates
        dates when the person is not available. The format of the date
        should be the same as the `dates` file.
  -d --dates_list <arg>  A text file with the masses dates. The format of
        the dates should be the same as the one used on the lector listing.
  -r --readings_list <args>  A text file with one reading title per line.
  -o --output_file <arg>  A HTML output file with the schedule.

Created on  Oct 12, 2022 by andrade.
Modified on Oct 12, 2022 by andrade.

BSD License
========================

Copyright (c) 2022, Carlos Eduardo de Andrade. All other rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are only permitted provided that the following conditions are
met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from collections import defaultdict
from datetime import datetime
from itertools import product
from pathlib import Path
from re import A
from typing import Dict, List
import sys

import docopt
from ortools.sat.python import cp_model

###############################################################################

def read_dates(dates_file: Path) -> List[str]:
    """
    Read dates from the given file. Dates are treated as simple strings.

    Args:
        - dates_file: a valid pure-text file or stringstream that
          can be opened. One date per line.

    Returns:
        A list of strings representing the dates.

    Todo:
        Process the input as datetime objects removing duplicates and invalid
        dates.
    """

    dates = []
    with open(dates_file, encoding="utf-8") as hd:
        for line in hd.readlines():
            dates.append(line.strip().lower())

    if len(dates) == 0:
        print(f"*** ERROR: '{dates_file}' is empty!")
        sys.exit(1)

    return dates

###############################################################################

def read_readings(readings_file: Path) -> List[str]:
    """
    Read the readings from the given file..

    Args:
        - readings_file: a valid pure-text file or stringstream that
          can be opened. One reading per line.

    Returns:
        A list of strings representing the readings.
    """

    readings = []
    with open(readings_file, encoding="utf-8") as hd:
        for line in hd.readlines():
            readings.append(line.strip().lower())

    if len(readings) == 0:
        print(f"*** ERROR: '{readings_file}' is empty!")
        sys.exit(1)

    return readings

###############################################################################

def read_lectors(lector_list_file: Path) -> List[dict]:
    """
    Read lector names and blocked dates from the given file.
    Dates are treated as simple strings, and should be compatible with dates
    from `read_dates()`.

    Args:
        - lector_list_file: a valid pure-text file or stringstream that
          can be opened. Each line should contain a lector name followed
          by dates when the lector is unavailable. For instance:

            John Doe,Oct-22
            Alice Joseph
            Bob Crapper,Nov-20,Dec-15

    Returns:
        A list of dictionaries representing named tuples such as

            [
                {
                    "name": "John Doe",
                    "blocked_dates": ["Oct-22"]
                },
                {
                    "name": "Alice Joseph",
                    "blocked_dates": []
                },
                {
                    "name": "Bob Crapper",
                    "blocked_dates": ["Nov-20", "Dec-15"]
                }
            ]

    Todo:
        - Process the input as datetime objects removing duplicates and invalid
          dates.
        - Remove duplicates names.
    """

    lectors = []
    with open(lector_list_file, encoding="utf-8") as hd:
        for line in hd.readlines():
            line = [x.strip() for x in line.split(",")]
            if len(line) == 0:
                continue
            lectors.append({
                "name": line[0],
                "blocked_dates": [x.lower() for x in line[1:]]
            })

    return lectors

###############################################################################

def build_schedule(lectors: List[dict], dates: List[str], readings: List[str]):
    """
    Create a constraint programming model to build a optimal schedule.

    The constraints are:
        1) For each day, each reading can be done for only one person;
        2) For each day, each lector does only one reading;
        3) Each lector must participate in all readings eventually.

    Also, lectors are not scheduled on given blocked dates.

    Finally, we maximize the minimum number of readings per lector.
    Such an objective function pushes for a load balancing between the lectors.

    Note that if we don't have enough days, Constraint 3 may be violated,
    and the model will be infeasible. Therefore, for only a few days,
    you may need to change the code and relax Constraint 3 or
    give extra "fake" days to ensure the constraint.

    Args:
        - lectors: a list as retunred by `read_lectors()`;
        - dates: a list of dates as the one returned by `read_dates()`;
        - readings: a list of strings describing the readings to be performed.

    Returns:
        A list of dictionaries representing the schedule such as

            [
                {
                    "reading": "1st reading",
                    "assignment": [
                        {
                            "date": "Oct-22",
                            "lector": "Alice Joseph"
                        },
                        {
                            "date": "Noc-24",
                            "lector": "John Doe"
                        }
                    ]
                },
                {
                    "reading": "2nd reading",
                    "assignment": [
                        {
                            "date": "Oct-22",
                            "lector": "Bob Crapper"
                        },
                        {
                            "date": "Noc-24",
                            "lector": "Alice Joseph"
                        }
                    ]
                }
            ]

    Todo:
        Relax Constraint 3 to avoid infeasibility.
    """

    ########################################
    # First, we create the variables
    ########################################
    model = cp_model.CpModel()

    slots = {}
    for lector in lectors:
        for date in dates:
            for reading in readings:
                slots[(lector["name"], date, reading)] = \
                    model.NewBoolVar(f"slot|{lector['name']}|{date}|{reading}")

    # Used to compute the person with least readings.
    minimal_readings = model.NewIntVar(0, len(dates), "minimal_readings")

    reading_amount = []
    for lector in lectors:
        name = lector["name"]
        tmp = model.NewIntVar(0, len(dates), f"reading_amount_{name}")
        model.Add(tmp == sum(
            slots[(name, date, reading)]
            for [date, reading] in product(dates, readings)
        ))
        reading_amount.append(tmp)

    ########################################
    # Constraints
    ########################################

    # Constraint 0: avoid assignment to blocked slots.
    for lector in lectors:
        name = lector["name"]
        for blocked_date in lector["blocked_dates"]:
            if blocked_date not in dates:
                print(f"Skipping {blocked_date} for {lector['name']}")
                continue
            for reading in readings:
                model.Add(slots[(name, blocked_date, reading)] == 0)
        # endfor dates
    # endfor lectors

    # Constraint 1: for each day, each reading can be done for only one person.
    for date in dates:
        for reading in readings:
            model.AddExactlyOne(
                slots[(lector["name"], date, reading)] for lector in lectors
            )

    # Constraint 2: for each day, each lector does only one reading.
    # TODO: we may need to change that to allow multiple reading for one
    # lector in the same day.
    for date in dates:
        for lector in lectors:
            model.AddAtMostOne(
                slots[(lector["name"], date, reading)] for reading in readings
            )

    # Constraint 3: each lector must participate in all readings eventually.
    for lector in lectors:
        for reading in readings:
            model.AddAtLeastOne(
                slots[(lector["name"], date, reading)] for date in dates
            )

    # Constraint 4: load balance: people should have
    # almost same number of readings
    model.AddMinEquality(minimal_readings, reading_amount)
    model.Maximize(minimal_readings)

    ########################################
    # Solving
    ########################################

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    counting = defaultdict(int)

    results = []
    if status == cp_model.OPTIMAL:
        for reading in readings:
            assignment = []
            for date in dates:
                for lector in lectors:
                    name = lector["name"]
                    if solver.Value(slots[(name, date, reading)]) == 1:
                        counting[name] += 1
                        assignment.append({
                            "date": date,
                            "lector": name
                        })
                # end for lector
            # end for dates
            results.append({
                "reading": reading,
                "assignment": assignment
            })
        # end for readings
    else:
        print("*** No solution found")

    # for [name, ctn] in counting.items():
    #     print(name, ctn)

    return results

###############################################################################

def print_results(results: List[dict], dates: List[str], outputfile: Path) \
        -> None:
    """
    Create a HTML file with the schedule.

    Args:
        - results: the schedule returned by `build_schedule()`;
        - dates: a list of dates as the one returned by `read_dates()`;
        - outputfile: a valid file to be written.

    Todo:
        Use some template library to make this function prettier.
    """

    header = """
<!DOCTYPE html>
<html dir="ltr" xml:lang="pt-br" lang="pt-br"
    xmlns="http://www.w3.org/1999/xhtml"
    itemscope itemtype="http://schema.org/WebPage">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0" />
    <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.6.0/css/all.css" crossorigin="anonymous" />
    <title>Escala de leitores</title>
    <style>
        h1 {
            color: #039;
            padding: 5px 0 5px 0;
            border: 2px solid #039;
            text-align: center;
            font-size: 150%;
            border-radius: 10px;
        }
        .my_table {
            width: 100%;
            margin-left: auto;
            margin-right: auto;
            text-align: center;
            vertical-align: middle;
        }
        .my_table th {
            background-color: rgb(192, 192, 192);
            font-size: 90%;
            color: #000000;
        }
    </style>
</head>
<body>
    <h1>Escala de leitores para missa em português</h1>"""
    footer = """
</body>
</html>
"""

    table = """
    <table class="my_table" border="1" cellpadding="2" cellspacing="2">
    <thead>
        <tr>
            <th></th>"""

    for date in dates:
        table += f"""
            <th>{date}</th>"""

    table += """
    </thead>
    <tbody>
    """

    for result in results:
        table += f"""
        <tr>
            <td>{result['reading']}</td>"""

        for pair in result["assignment"]:
            table += f"""
            <td>{pair['lector']}</td>"""

        table += """
        </tr>"""

    table += """
    </tbody>
    </table>"""

    additional_info = f"""
<p>
<ul class='fa-ul'>
    <li><i class="fa-li fas fa-chevron-right" style="color: steelblue;"></i>
    Esta agenda é automatica e otimamente balanceada de tal maneira que todos
    leitores tenham aproximadamente o mesmo número de leituras no decorrer
    da agenda;
    </li>
    <li><i class="fa-li fas fa-chevron-right" style="color: steelblue;"></i>
    Todos leitores terão a oportunidade de fazer um tipo de leitura, ou seja,
    em uma missa ele ou ela lerá a 1a leitura, em outra rezará o salmo ou
    ainda fará as orações da assembléia;
    </li>
    <li><i class="fa-li fas fa-chevron-right" style="color: steelblue;"></i>
    Não temos leitores repetidos em um mesmo dia. Mas se necessário,
    é possível configurar o escalonador para o fazer;
    </li>
    <li><i class="fa-li fas fa-chevron-right" style="color: steelblue;"></i>
    Também assumimos que todos estão disponíveis nas datas previstas das
    missas. Se você sabe de um dia que não poderá comparecer de antemão, nos
    avise para que possamos refazer a agenda;
    </li>
    <li><i class="fa-li fas fa-chevron-right" style="color: steelblue;"></i>
    Essa agenda é construída usando programação matemática
    usando
    <a href="https://github.com/ceandrade/lector_scheduling">
    este código.
    </a>
    </li>
</ul>
</p>
<p>Atualizado em {datetime.strftime(datetime.now(), '%Y-%m-%d')}.</p>
"""

    with open(outputfile, mode="w", encoding="utf-8") as hd:
        hd.write(header)
        hd.write(table)
        hd.write(additional_info)
        hd.write(footer)

###############################################################################

def main(args: Dict[str, str]) -> None:
    """
    The main fuction.

    Args:
        - args: a dictionary of the command line arguments.
    """

    dates = read_dates(Path(args["--dates_list"]))
    lectors = read_lectors(Path(args["--lectors_list"]))
    readings = read_readings(Path(args["--readings_list"]))

    results = build_schedule(lectors, dates, readings)

    print_results(results, dates, Path(args["--output_file"]))

###############################################################################

if __name__ == "__main__":
    arguments = docopt.docopt(__doc__)
    main(arguments)
