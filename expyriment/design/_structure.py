"""
The design._structure module of expyriment.

This module contains a class implementing the experiment structure.

"""

__author__ = 'Florian Krause <florian@expyriment.org>, \
Oliver Lindemann <oliver@expyriment.org>'
__version__ = ''
__revision__ = ''
__date__ = ''


import os
import sys
import types
try:
    import csv
except ImportError:
    from expyriment.misc import _csv_reader_android as csv
from copy import deepcopy

import defaults
import expyriment
from expyriment.misc import constants
from expyriment.misc import Clock
import randomize
import permute


class Experiment(object):
    """A class implementing a basic experiment."""

    def __init__(self, name=None, foreground_colour=None,
                 background_colour=None, text_font=None, text_size=None,
                 filename_suffix=None):
        """Create an experiment.

        Parameters
        ----------
        name : str, optional
            name of the experiment
        foreground_colour : (int, int, int), optional
        background_colour : (int,int,int), optional
        text_font : str, optional
        text_size : int, optional
        filename_suffix : str, optional
            additional suffix that will be added to the main event
            and data filename

        """
        if name is not None:
            self._name = name
        elif defaults.experiment_name is not None:
            self._name = defaults.experiment_name
        else:
            self._name = os.path.split(sys.argv[0])[1].replace(".py", "")
        if background_colour is not None:
            self._background_colour = background_colour
        else:
            self._background_colour = \
                    defaults.experiment_background_colour
        if foreground_colour is not None:
            self._foreground_colour = foreground_colour
        else:
            self._foreground_colour = \
                    defaults.experiment_foreground_colour
        if text_font is not None:
            self._text_font = text_font
        else:
            self._text_font = defaults.experiment_text_font
        if text_size is not None:
            self._text_size = text_size
        else:
            self._text_size = defaults.experiment_text_size
        if filename_suffix is not None:
            self._filename_suffix = filename_suffix
        else:
            self._filename_suffix = defaults.experiment_filename_suffix

        self.clear_bws_factors()
        self._data_variable_names = []
        self._experiment_info = []
        self._blocks = []
        self._block_id_counter = 0

        self._is_started = False
        self._is_initialized = False
        self._keyboard = None
        self._clock = None
        self._subject = None
        self._screen = None
        self._data = None
        self._events = None
        self._log_level = 0  # will be set from initialize
        self._wait_callback_function = None

    @property
    def name(self):
        """Getter for name."""

        return self._name

    @property
    def blocks(self):
        """Getter for blocks."""

        return self._blocks

    @property
    def background_colour(self):
        """Getter for background_colour."""

        return self._background_colour

    @property
    def foreground_colour(self):
        """Getter for foreground_colour."""

        return self._foreground_colour

    @property
    def text_font(self):
        """Getter for text_font."""

        return self._text_font

    @property
    def text_size(self):
        """Getter for text_size."""

        return self._text_size

    @property
    def filename_suffix(self):
        """Getter for filename suffix."""

        return self._filename_suffix
    @property
    def screen(self):
        """Getter for global screen."""

        return self._screen

    @property
    def data(self):
        """Getter for main data file."""

        return self._data

    @property
    def events(self):
        """Getter for main event files."""

        return self._events

    @property
    def log_level(self):
        """Getter for event logging. """

        return self._log_level

    @property
    def clock(self):
        """Getter for global clock."""

        return self._clock

    @property
    def keyboard(self):
        """Getter for global keyboard."""

        return self._keyboard

    @property
    def subject(self):
        """Getter for global subject."""

        return self._subject

    @property
    def is_started(self):
        """Getter for is_started."""

        return self._is_started

    @property
    def is_initialized(self):
        """Getter for is_initialized."""

        return self._is_initialized

    def __str__(self):
        tmp_str = "Experiment: {0}\n".format(repr(self.name))
        if len(self.bws_factor_names) <= 0:
            tmp_str = tmp_str + "no between subject factors\n"
        else:
            tmp_str = tmp_str + "between subject factors (permutation type: "
            if self.bws_factor_randomized:
                tmp_str = tmp_str + "random)\n"
            else:
                tmp_str = tmp_str + "latin square)\n"
            for f in self.bws_factor_names:
                tmp_str = tmp_str + "   {0} = {1}\n".format(f,
                                                        self._bws_factors[f])
        for block in self.blocks:
            tmp_str = tmp_str + "{0}\n".format(block.summary)
        return tmp_str

    @property
    def data_variable_names(self):
        """Getter for data_variable_names."""

        return self._data_variable_names

    @data_variable_names.setter
    def data_variable_names(self, value):
        """Setter for data_variable_names."""

        self.clear_data_variable_names()
        self.add_data_variable_names(value)

    def clear_data_variable_names(self):
        """Remove all data variable names from design."""

        self._data_variable_names = []
        if self.data is not None:
            self.data.clear_variable_names()

    def add_data_variable_names(self, variable_names):
        """Add data variable names to the design.

        Parameters
        ----------
        variables : str or lst of str
            variable names

        """
        if variable_names is None:
            return
        if type(variable_names) is not list:
            variable_names = [variable_names]
        self._data_variable_names.extend(variable_names)
        if self.data is not None:
            self.data.add_variable_names(variable_names)

    @property
    def experiment_info(self):  # experiment_info can not be cleared!
        """Getter for experiment_info."""

        return self._experiment_info

    def add_experiment_info(self, text):
        """Add experiment information to the design.

        Parameters
        ----------
        text : string or list of str
            text lines to be added as experiment information

        """

        if text is None:
            return
        if type(text) is not list:
            text = [text]
        self._experiment_info.extend(text)
        if self.data is not None:
            self.data.add_experiment_info(text)

    @property
    def bws_factor_randomized(self):
        """Getter for bws_factor_randomized.

        Notes
        -----
        Is between subject factor randomized? (True/False).

        If True conditions will be assigned randomized
        otherwise (default) conditions will be systematically permuted across
        subjects.

        """

        return self._bws_factor_randomized

    @bws_factor_randomized.setter
    def bws_factor_randomized(self, value):
        """Setter for bws_factor_randomized."""

        self._bws_factor_randomized = value

    def add_bws_factor(self, factor_name, conditions):
        """Add a between subject factor.

        The defined between subject factor conditions will be permuted across
        the subjects. Factors that are added first are treated as
        hierarchically higher factors while permutation.

        Parameters
        ----------
        factor_name : str
            the name of the between subject factor
        conditions : list
            possible conditions of the between subject factor

        """

        if type(conditions) is not list:
            conditions = [conditions]
        self._bws_factors[factor_name] = conditions
        self._bws_factors_names.append(factor_name)
        self._randomized_condition_for_subject[factor_name] = {}

    def get_bws_factor(self, factor_name):
        """Return all conditions of this between subject factor."""

        try:
            cond = self._bws_factors[factor_name]
        except:
            return None
        return cond

    def get_permuted_bws_factor_condition(self, factor_name, subject_id=None):
        """Get the between subject factor condition for a subject.

        The condition for the current subject will be returned, if expyriment
        is running and the function is called without a subject_id.
        If the function is called with a subject_id, the condition for this
        particular subject will be returned.

        Parameters
        ----------
        factor_name : str
        subject_id : str, optional
            (default=None)

        Returns
        -------
        cond : str
            condition for the current subject

        """

        if subject_id is None:
            if self.subject is None:  # No current subject id defined
                return None
            else:  # Use current subject
                return self.get_permuted_bws_factor_condition(
                    factor_name, subject_id=self.subject)
        else:
            conditions = self.get_bws_factor(factor_name)
            if conditions is None:
                return None  # Factor not defined
            else:
                cond_idx = 0
                if self.bws_factor_randomized:
                    try:
                        cond_idx = self._randomized_condition_for_subject[
                                    factor_name][subject_id]
                    except:  # If not yet randomized for this subject, do it
                        cond_idx = randomize.rand_int(
                            0, len(self._bws_factors[factor_name]) - 1)
                        self._randomized_condition_for_subject[
                                            factor_name][subject_id] = cond_idx

                else:  # Permutation
                    # (n_cond_lower_fac) total number of conditions for all
                    # hierarchically lower factors
                    n_cond_lower_fac = self.n_bws_factor_conditions
                    for fac in self.bws_factor_names:
                        n_cond_lower_fac -= len(self.get_bws_factor(fac))
                        if fac is factor_name:
                            break
                    if n_cond_lower_fac <= 0:
                        n_cond_lower_fac = 1
                    cond_idx = ((subject_id - 1) / n_cond_lower_fac) % \
                            len(self.get_bws_factor(fac))
                return self._bws_factors[factor_name][cond_idx]

    def clear_bws_factors(self):
        """Remove all between subject factors from design."""

        self._bws_factors = {}

        # Can't use dict_keys, because dicts don't keep the order
        self._bws_factors_names = []

        self._randomized_condition_for_subject = {}
        self.bws_factor_randomized = False

    @property
    def bws_factor_names(self):
        """Getter for factors keys."""
        return self._bws_factors_names

    @property
    def n_bws_factor_conditions(self):
        """Getter for n_bws_factor_conditions.

        Total number of conditions in all bws_factors.

        """

        n = 0
        for fn in self.bws_factor_names:
            n += len(self.get_bws_factor(fn))
        return n

    def set_log_level(self, loglevel):
        """Set the log level of the current experiment

        Parameters
        ----------
        loglevel : int
            The log level (0, 1,3) of the experiment.

        Notes
        -----
        There are three event logging levels:
        * O no event logging
        * 1 normal event logging (logging of all input & output events)
        * 2 intensive logging. Logs much more. Please use this only for
            debugging proposes.

        In most cases, it should be avoided to switch of logging (loglevel=0).
        It log files become to big due to certain repetitive events, it is
        suggested to switch of the logging of individual stimuli or IO event.
        (see the method `.set_logging()` of this objects)

        The logging of events can be also changed before initialize via the
        default value `expyriment.control.defaults.event_logging`.

        """

        self._log_level = int(loglevel)

    def add_block(self, block, copies=1):
        """Add a block to the experiment.

        Parameters
        ----------
        block : design.Block
            block to add
        copies : int, optional
            number of copies to add (default = 1)

        """

        for _x in range(0, copies):
            self._blocks.append(block.copy())
            self._blocks[-1]._id = self._block_id_counter
            self._block_id_counter += 1

        expyriment._active_exp._event_file_log(
                                    "Experiment,block added,{0},{1}".format(
                                    self.name, self._blocks[-1]._id), 2)

    def remove_block(self, position):
        """Remove block from experiment.

        If no position is given, the last one is removed.

        Parameters
        ----------
        position : int
            position of the block to be removed

        """

        block = self._blocks.pop(position)

        expyriment._active_exp._event_file_log(
            "Experiment,block removed,{0},{1}".format(self.name, block.id), 2)

    def clear_blocks(self):
        """Remove all blocks from experiment."""

        self._blocks = []
        self._block_id_counter = 0

        expyriment._active_exp._event_file_log("Experiment,blocks cleared", 2)

    def order_blocks(self, order):
        """Order the blocks.

        Parameters
        ----------
        order : list
            list with the new order of positions

        """

        if not len(order) == len(self._blocks):
            raise ValueError("Given order has wrong number of items!")
        blocks_new = []
        for position in order:
            blocks_new.append(self._blocks[position])
        self._blocks = blocks_new

    @property
    def n_blocks(self):
        """Getter for n_blocks.

        Number of blocks.

        """

        return len(self._blocks)

    def swap_blocks(self, position1, position2):
        """Swap two blocks.

        Parameters
        ----------
        position1 : int
            position of first block
        position2 : int
            position of second block

        """

        if position1 < len(self._blocks) and position2 < len(self._blocks):
            self._blocks[position1], self._blocks[position2] = \
                    self._blocks[position2], self._blocks[position1]
            return True
        else:
            return False

    def shuffle_blocks(self):
        """Shuffle all blocks."""

        randomize.shuffle_list(self._blocks)

    def permute_blocks(self, permutation_type, factor_names=None,
                       subject_id=None):
        """Permute the blocks.

        Parameters
        ----------
        permutation_type : int (permutation type)
            type of block order permutation (permutation type)
            Permutation types defined in misc.constants:
            P_BALANCED_LATIN_SQUARE, P_CYCLED_LATIN_SQUARE, and P_RANDOM
        factor_names : list (of strings), optional
            list of the factor names to be considered while permutation.
            If factor_names are not defined (None) all factors will be used.
        subject_id : int, optional
            subject number for this permutation
            If subject_id is defined or none (default) and experiment has
            been started, the current subject number will be used

        """

        if subject_id is None:
            if self.subject is None:
                raise RuntimeError("If Expyriment is not started, \
a subject number needs to be defined for the permutation.")
            else:
                subject_id = self.subject

        if not permute.is_permutation_type(permutation_type):
                raise AttributeError("{0} is a unknown permutation \
type".format(permutation_type))
        if factor_names is None:
            factor_names = self.block_list_factor_names

        # Get the condition combinations for the specified factors:
        all_factor_combi = []
        for b in self.blocks:
            combi = []
            for f in factor_names:
                combi.append([f, b.get_factor(f)])
            new = True
            for c in all_factor_combi:
                if c == combi:
                    new = False
            if new:  # Add only a new combination
                all_factor_combi.append(combi)

        # Get the permutation
        if permutation_type == constants.P_BALANCED_LATIN_SQUARE:
            permutation = permute.balanced_latin_square(all_factor_combi)
            idx = (subject_id - 1) % len(permutation)
            permutation = permutation[idx]
        elif permutation_type == constants.P_CYCLED_LATIN_SQUARE:
            permutation = permute.cycled_latin_square(all_factor_combi)
            idx = (subject_id - 1) % len(permutation)
            permutation = permutation[idx]
        else:
            randomize.shuffle_list(all_factor_combi)
            permutation = all_factor_combi

        tmp = self._blocks
        self._blocks = []
        for search_combi in permutation:
            # Search tmp block for this comb
            # And add all fitting blocks  (multiple addings possible)
            for b in tmp:
                combi = []
                for f in factor_names:
                    combi.append([f, b.get_factor(f)])
                if combi == search_combi:
                    self._blocks.append(b)

    def sort_blocks(self):
        """Sort the blocks according to their indices from low to high."""

        blocks_new = []
        id_list = [x.id for x in self._blocks]
        id_list.sort()
        for id in id_list:
            position = [i for i, x in enumerate(self._blocks) \
                         if x.id == id][0]
            blocks_new.append(self._blocks[position])
        self._blocks = blocks_new

    def find_block(self, id):
        """Find the position of a block, given the id.

        Parameters
        ----------
        id : int
            block id to look for

        Returns
        -------
        pos: int
         positions as a list or None if not in block list.

        """

        positions = [i for i, x in enumerate(self._blocks) if x.id == id]
        if positions:
            return positions

    @property
    def trial_factor_names(self):
        """Getter for trial_factor_nanes.

        Get all factor names defined in the trial lists of all blocks.

        """

        factors = []
        for bl in self.blocks:
            factors.extend(bl.trial_factor_names)
        return list(set(factors))

    @property
    def block_list_factor_names(self):
        """Getter for block_list_factor_names.

        Get all factor names defined in all blocks.

        """

        factors = []
        for bl in self.blocks:
            factors.extend(bl.factor_names)
        return list(set(factors))

    @property
    def design_as_text(self):
        """Getter for desing_as_text.

        Trial list as csv table.

        """

        rtn = "#exp: {0}\n".format(self.name)
        if len(self.experiment_info) > 0:
            for txt in self.experiment_info:
                rtn += "#xpi: {0}\n".format(txt)
        if len(self.bws_factor_names) > 0:
            for factor_name in self.bws_factor_names:
                rtn += "#bws: {0}=".format(factor_name)
                for txt in self.get_bws_factor(factor_name):
                    rtn += "{0},".format(txt)
                rtn = rtn[:-1] + "\n"  # delete last comma
            rtn += "#bws-rand: {0}\n".format(int(self.bws_factor_randomized))
        if len(self.data_variable_names) > 0:
            rtn += "#dvn: "
            for txt in self.data_variable_names:
                rtn += "{0},".format(txt)
            rtn = rtn[:-1] + "\n"

        rtn += "block_cnt,block_id"
        bl_factors = self.block_list_factor_names
        factors = self.trial_factor_names
        for f in bl_factors:
            rtn += ",block_{0}".format(f)
        rtn += ",trial_cnt,trial_id"
        for f in factors:
            rtn += ",{0}".format(f)

        for bl_cnt, bl in enumerate(self.blocks):
            for tr_cnt, tr in enumerate(bl.trials):
                rtn += "\n{0},{1}".format(bl_cnt, bl.id)
                for f in bl_factors:
                    rtn += ",{0}".format(bl.get_factor(f))
                rtn += ",{0},{1}".format(tr_cnt, tr.id)
                for f in factors:
                    rtn += ",{0}".format(tr.get_factor(f))

        return rtn

    def save_design(self, filename):
        """Save the design as list of trials to a csv file.

        The function considers only the defined trial factors and not the
        added stimuli.

        Notes
        -----
        The current version of this function does not handle between_subject
        factors and data_variables.

        Parameters
        ----------
        filename : str
            name (fullpath) of the csv file (str)

        """

        with open(filename, 'w') as f:
            f.write(self.design_as_text)

    def load_design(self, filename):
        """Load the design from a csv file containing list of trials.

        The function considers only the defined trial factors and not the
        added stimuli. The existing design will be deleted.

        Notes
        -----
        The current version of this function does not handle between_subject
        factors and data_variables.

        Parameters
        ----------
        filename : str
            name (fullpath) of the csv file (str)

        """

        delimiter = ","
        self.clear_blocks()
        block_factors = {}
        trial_factors = {}
        with open(filename, 'r') as fl:
            for ln in fl:
                if ln[0] == "#":
                    if ln.startswith("#exp:"):
                        self._name = ln[6:].strip()
                    elif ln.startswith("#xpi:"):
                        self.add_experiment_info(ln[6:].strip())
                    elif ln.startswith("#dvn:"):
                        for tmp in ln[6:].split(","):
                            self.add_data_variable_names(tmp.strip())
                    elif ln.startswith("#bws-rand:"):
                        self.bws_factor_randomized = (ln[11] == "1")
                    elif ln.startswith("#bws:"):
                        tmp = ln[6:].split("=")
                        print tmp[1].strip().split(",")
                        self.add_bws_factor(tmp[0], tmp[1].strip().split(","))

                else:  # data line
                    if len(block_factors) < 1:
                        # read first no-comment line --> varnames
                        for col, var in enumerate(ln.split(delimiter)):
                            var = var.strip()
                            if var.startswith("block_"):
                                var = var.replace("block_", "")
                                block_factors[col] = var
                            elif var.startswith("trial_"):
                                var = var.replace("trial_", "")
                                trial_factors[col] = var
                            else:
                                trial_factors[col] = var

                        if not("cnt" in block_factors.values() and
                                    "id" in block_factors.values() and
                                    "cnt" in trial_factors.values() and
                                    "id" in trial_factors.values()):
                            message = "Can't read design file. " + \
                                    "The file '{0}' ".format(filename) + \
                                    "does not contain a Expyriment trial list."
                            raise IOError(message)
                    else:
                        block_cnt = None
                        trial_cnt = None
                        # read data
                        for col, val in enumerate(ln.split(delimiter)):
                            val = val.strip()
                            # try to convert to number
                            if val.find(".") >= 0:
                                try:
                                    val = float(val)
                                except:
                                    pass
                            else:
                                try:
                                    val = int(val)
                                except:
                                    pass
                            # set value to block or trial
                            if col in block_factors:
                                if block_factors[col] == "cnt":
                                    block_cnt = val
                                    while len(self.blocks) < block_cnt + 1:
                                        self.add_block(Block())
                                elif block_factors[col] == "id":
                                    self.blocks[block_cnt]._id = val
                                else:
                                    self.blocks[block_cnt].set_factor(
                                                    block_factors[col], val)

                            if col in trial_factors:
                                if trial_factors[col] == "cnt":
                                    trial_cnt = val
                                    while len(self.blocks[block_cnt].trials)\
                                                             < trial_cnt + 1:
                                        self.blocks[block_cnt].add_trial(
                                                                    Trial())
                                elif trial_factors[col] == "id":
                                    self.blocks[block_cnt].trials[trial_cnt].\
                                                            _id = val
                                else:
                                    self.blocks[block_cnt].trials[trial_cnt].\
                                            set_factor(trial_factors[col], val)

    def _event_file_log(self, log_text, log_level=1):
        # log_level 1 = default, 2 = extensive, 0 or False = off
        """ Helper function to log event in the global experiment event file"""
        if self.is_initialized and\
               self._log_level > 0 and\
               self._log_level >= log_level and \
               self.events is not None:
            self.events.log(log_text)

    def _event_file_warn(self, warning, log_level=1):
        """ Helper function to log event in the global experiment event file"""
        if self.is_initialized and\
                self._log_level > 0 and\
                self._log_level >= log_level and \
                self.events is not None:
            self.events.log(warning)

    def log_design_to_event_file(self, additional_comment=""):
        """Log the design (as comment) to the current main event file.

        If no experiment is initialized or no event file exists the function
        will not do anything. This function will be automatically called after
        an experiment has been started.

        Notes
        -----
        See also save_design().

        Parameters
        ----------
        additional_comment : str, optional
            additional comment that will be logged

        """

        if self.is_initialized and self.events is not None:
            self.events.log("design,log,{0}".format(additional_comment))
            for ln in self.design_as_text.splitlines():
                self.events.write_comment("design: {0}".format(ln).replace(
                                                                    ":#", "-"))
            self.events.log("design,logged,{0}".format(additional_comment))

    def register_wait_callback_function(self, function):
        """Register a wait callback function.

        Notes
        -----
        CAUTION! If wait callback function takes longer than 1 ms to process,
        Expyriment timing will be affected!

        The registered wait callback function will be repetitively executed in
        all Expyriment wait and event loops that wait for an external input.
        That is, they are executed by the following functions (at least once!):

        - control.wait_end_audiosystem
        - misc.clock.wait
        - misc.clock.wait_seconds
        - misc.clock.wait_minutes
        - io.keyboard.wait
        - io.keyboard.wait_char
        - io.buttonbox.wait
        - io.gamepad.wait_press
        - io.triggerinput.wait
        - io.mouse.wait_press
        - io.serialport.read_line
        - io.textinput.get
        - stimulus.video.wait_frame
        - stimulus.video.wait_end

        Parameters
        ----------
        function : function
            wait function (function)

        """

        if type(function) == types.FunctionType:
            self._wait_callback_function = function
        else:
            raise AttributeError("register_wait_callback_function requires " +
                                 "a function as parameter")

    def unregister_wait_callback_function(self):
        """Unregister wait function."""

        self._wait_callback_function = None

    def _execute_wait_callback(self):
        """Execute wait function.

        Returns True if wait function is defined and executed.

        """

        if self._wait_callback_function is not None:
            self._wait_callback_function()
            return True
        else:
            return False


class Block(object):
    """A class implementing an experimental block."""

    _trial_cnt_variable_name = "trial_cnt"  # variable names for csv in/output
    _trial_id_variable_name = "trial_id"

    def __init__(self, name=None):
        """Create a block.

        Parameters
        ----------
        name : str, optional
            name of the block

        """

        if name is not None:
            self._name = name
        else:
            self._name = defaults.block_name

        self._factors = {}
        self._trials = []
        self._trial_id_counter = 0
        self._id = None

    @property
    def name(self):
        """Getter for name."""

        return self._name

    @property
    def id(self):
        """Getter for id."""

        return self._id

    @property
    def trials(self):
        """Getter for trials."""

        return self._trials

    def __str__(self):
        return self._get_summary(True)

    @property
    def summary(self):
        """Getter for summary."""

        return self._get_summary(False)

    def _get_summary(self, include_trial_IDs):
        """Return a summary of the trials as string."""

        if self.name is None:
            name = ""
        else:
            name = self.name
        rtn = """Block {0}: {1}
    block factors: {2}
    n trials: {3}""".format(self.id, name, \
                     self.factors_as_text, \
                     len(self.trials))

        if include_trial_IDs:
            rtn = rtn + """
    trial IDs={0}""".format([t.id for t in self.trials])
        rtn = rtn + """
    trial factors:"""
        for f in self.trial_factor_names:
            val = []
            for tf in self.get_trial_factor_values(f):
                if tf not in val:
                    val.append(tf)
            val.sort()
            rtn = rtn + """
    {0}={1}""".format(f, val)

        return rtn

    @property
    def factors_as_text(self):
        """Getter for factors_as_text.

        Return all factor names and values as string line.

        """

        all_factors = ""
        for f in self.factor_names:
            all_factors = all_factors + "{0}={1}, ".format(f, \
                                self.get_factor(f))
        all_factors = all_factors.rstrip()
        if len(all_factors) >= 1 and all_factors[-1] == ",":
            all_factors = all_factors[:-1]
        return all_factors

    def set_factor(self, name, value):
        """Set a factor for the block.

        Parameters
        ----------
        name : str
            factor name
        value : str or numeric
            factor value

        """

        if type(value) in [types.StringType, types.IntType, types.FloatType]:
            self._factors[name] = value
        else:
            message = "Factor values or factor conditions must to be a " + \
                    "String or a Number (i.e. float or integer).\n " + \
                    "{0} is not allowed.".format(type(value))
            raise TypeError(message)

    def get_factor(self, name):
        """Get a factor of the block.

        Parameters
        ----------
        name : str
            factor name (str)

        """

        try:
            rtn = self._factors[name]
        except:
            rtn = None
        return rtn

    @property
    def factor_dict(self):
        """The dictionary with all factors of the block."""

        return self._factors

    def clear_factors(self):
        """Clear all factors."""

        self._factors = {}

    @property
    def factor_names(self):
        """Getter for factor_names.

        Factor keys.

        """

        return self._factors.keys()

    def get_random_trial(self):
        """Returns a randomly selected trial.

        Notes
        -----
        This function is useful for compiling training blocks.

        Returns
        -------
        rnd : design.Trial
            random Expyriment trial
        """

        rnd = randomize.rand_int(0, len(self._trials) - 1)
        return self._trials[rnd]

    def add_trial(self, trial, copies=1, random_position=False):
        """Add trial to the block.

        Parameters
        ----------
        trial : design.Trial
            trial to add
        copies : int, optional
            number of copies to add (default = 1)
        random_position : bool, optional
            True  = insert trials at random position,
            False = append trials at the end (default=False)

        """

        for _x in range(0, copies):
            if random_position:
                pos = randomize.rand_int(0, len(self._trials))
                self._trials.insert(pos, trial.copy())
            else:
                self._trials.append(trial.copy())
            self._trials[-1]._id = self._trial_id_counter
            self._trial_id_counter += 1

        log_txt = "Block,trial added,{0}, {1}".format(self.name,
                                                      self._trials[-1]._id)
        if random_position:
            log_txt = log_txt + ", random position"
        expyriment._active_exp._event_file_log(log_txt, 2)

    def remove_trial(self, position):
        """Remove a trial.

        Parameters
        ----------
        position : int
            position of the trial

        """

        trial = self._trials.pop(position)

        expyriment._active_exp._event_file_log("Block,trial removed,{0},{1}"\
                                        .format(self.id, trial.id), 2)

    def clear_trials(self):
        """Clear all trials."""

        self._trials = []
        self._trial_id_counter = 0

        expyriment._active_exp._event_file_log("Block,trials cleared", 2)

    @property
    def n_trials(self):
        """Getter for n_trials.

        Number of trials.

        """

        return len(self._trials)

    @property
    def trial_factor_names(self):
        """Getter for trial_factor_names.

        Get all factor names defined in trial list.

        """

        if len(self.trials) < 1:
            return []
        rtn = self.trials[0].factor_names
        for tr in self.trials:
            for new_fac in tr.factor_names:
                is_new = True
                for old_fac in rtn:
                    if old_fac == new_fac:
                        is_new = False
                        break
                if is_new:
                    rtn.append(new_fac)
        return rtn

    def get_trial_factor_values(self, name):
        """Return a list of the values of a certain factor for all trials.

        Parameters
        ----------
        name : str
            name of the factor

        """

        rtn = []
        for trial in self.trials:
            rtn.append(trial.get_factor(name))
        return rtn

    @property
    def design_as_text(self):
        """Getter for design_as_text.

        List of trial factors as csv table.

        The list considers only the defined trial factors and not the
        added stimuli.

        """

        rtn = "{0},{1}".format(self._trial_cnt_variable_name,
                               self._trial_id_variable_name)
        factors = self.trial_factor_names
        for f in factors:
            rtn = rtn + ",{0}".format(f)
        for cnt, tr in enumerate(self.trials):
            rtn = rtn + "\n{0},{1}".format(cnt, tr.id)
            for f in factors:
                rtn = rtn + ",{0}".format(tr.get_factor(f))
        return rtn

    def save_design(self, filename):
        """Save the list of trials to a csv file.

        The function considers only the defined trial factors and not the
        added stimuli.

        Parameters
        filename  -- name (fullpath) of the csv file

        """

        with open(filename, 'w') as f:
            f.write(self.design_as_text)

    def read_design(self, filename):
        """Reads a list of trials from a csv file and clears the old block
        design.

        The function considers only the trial factors and not the added
        stimuli. All factors will be read in as text strings and not casted to
        numericals. Please do this manually if required.

        Parameters
        ----------
        filename : str
            name (fullpath) of the csv file (str)

        """

        tmp = Block()
        tmp.add_trials_from_csv_file(filename)
        fac_names = tmp.trial_factor_names

        self.clear_factors()
        self.clear_trials()

        for tr in tmp.trials:
            new = Trial()
            for fac in fac_names:
                if fac == self._trial_cnt_variable_name:
                    pass
                elif fac == self._trial_id_variable_name:
                    new._id = int(tr.get_factor(fac))
                else:
                    new.set_factor(fac, tr.get_factor(fac))
            self.add_trial(new)

    def add_trials_from_csv_file(self, filename):
        """Read a list of trials from csv-file and append the new trials to the
        block. Trials are defined as combinations of trial factors.

        **csv-file specifications**

            The first row of the csv-file specifies the factor names. Each
            following row describes one trial. Each row must have the same
            amount of columns.

        Notes
        ------
        All factors will be read in as text strings and not casted to
        numericals. Please do this manually if required.

        Parameters
        ----------
        filename : str
            name (fullpath) of the csv file (str)

        """

        factor_names = []
        with open(filename, "rb") as f:
            reader = csv.reader(f)
            for r_cnt, row in enumerate(reader):
                if r_cnt == 0:
                    factor_names = deepcopy(row)
                else:
                    trial = Trial()
                    for c_cnt in range(0, len(row)):
                        trial.set_factor(factor_names[c_cnt], row[c_cnt])
                    self.add_trial(trial)

    def order_trials(self, order):
        """Order the trials.

        Parameters
        ----------
        order : list
            list with the new order of positions

        """

        if not len(order) == len(self._trials):
            raise ValueError("Given order has wrong number of items!")
        trials_new = []
        for position in order:
            trials_new.append(self._trials[position])
        self._trials = trials_new

    def swap_trials(self, position1, position2):
        """Swap two trials.

        Parameters
        ----------
        position1 : int
            position of first trial
        position2 : int
            position of second trial

        """

        if position1 < len(self._trials) and position2 < len(self._trials):
            self._trials[position1], self._trials[position2] = \
                    self._trials[position2], self._trials[position1]
            return True
        else:
            return False

    @property
    def max_trial_repetitions(self):
        """Getter for max_trial_repetitions.

        Returns the maximum number of immediate trial repetitions.

        """

        tmp = []
        for t in self._trials:
            tmp.append(t.factors_as_text)

        max_reps = 0
        cnt = 0
        for x in range(1, len(tmp) - 1):
            if tmp[x - 1] == tmp[x]:
                cnt += 1
                if cnt > max_reps:
                    max_reps = cnt
            else:
                cnt = 0
        return max_reps

    def shuffle_trials(self, method=0, max_repetitions=None):
        """Shuffle all trials.

        The function returns False if no randomization could be found that
        fulfills the max immediate trial repetition criterion. The different
        type of trials are only defined by the factors. Shuffle does not
        take into account the added stimuli.

        The following randomization methods are defined:

                0 = total randomization of trial order (default),

                1 = randomization within small miniblocks. Each miniblock
                contains one trial of each type (only defined by factors!).
                In other words, copies of one trial type are always in
                different miniblocks.

        Parameters
        ----------
        method : int, optional
            method of trial randomization (default=0)
        max_repetitions : int, optional
            maximum number of allowed immediate repetitions.
            If None the repetition criterion will be ignored

        Returns
        -------
        succeeded : bool

        """

        start = Clock._cpu_time()
        cnt = 0
        while True:
            cnt += 1
            self._shuffle_trials(method)
            if max_repetitions is None or \
                (self.max_trial_repetitions <= max_repetitions):
                return True
            else:
                if (Clock._cpu_time() - start) * 1000 >= \
                                                    defaults.max_shuffle_time:
                    print "Warning: Could not find an appropriate trial " + \
                          "randomization ({0} attempts)!".format(cnt)
                    return False

    def _shuffle_trials(self, method):
        """actual implementation of the trial shuffling"""
        if method == 1:  # shuffling blockwise
            cp = self.copy()
            randomize.shuffle_list(cp._trials)
            self._trials = []
            types_occured = []
            cnt = 0
            while len(cp._trials) > 0:
                tr = cp._trials[cnt]
                new = True
                tr_type = tr.factors_as_text
                for occ in types_occured:
                    if tr_type == occ:
                        new = False
                        break
                if new:
                    self._trials.append(tr)
                    cp._trials.pop(cnt)
                    types_occured.append(tr_type)
                    cnt = 0
                else:
                    cnt = cnt + 1
                    if cnt >= len(cp._trials):
                        types_occured = []
                        cnt = 0
        else:
            randomize.shuffle_list(self._trials)

    def sort_trials(self):
        """Sort the trials according to their indices from low to high."""

        trials_new = []
        id_list = [x.id for x in self._trials]
        id_list.sort()
        for _id in id_list:
            position = [i for i, x in enumerate(self._trials) \
                         if x.id == _id][0]
            trials_new.append(self._trials[position])
        self._trials = trials_new

    def find_trial(self, id):
        """Find the positions of a trial.

        Parameters
        -----------
        id : int
            trial id to look for

        Returns
        -------
        pos : list
            positions as a list or None if not in trial list.

        """

        positions = [i for i, x in enumerate(self._trials) if x.id == id]
        if positions:
            return positions

    def copy(self):
        """Return a copy of the block."""

        owntrials = []
        triallist = []
        for trial in self._trials:
            owntrials.append(trial)
            triallist.append(trial.copy())
        self._trials = None
        rtn = deepcopy(self)
        self._trials = owntrials
        rtn._trials = triallist
        return rtn


class Trial(object):
    """A class implementing an experimental trial."""

    def __init__(self):
        """Create a Trial."""

        self._stimuli = []
        self._factors = {}
        self._id = None

    @property
    def stimuli(self):
        """Getter for stimuli."""

        return self._stimuli

    @property
    def id(self):
        """Getter for id."""

        return self._id

    def __str__(self):
        return """
        Trial:   {0}

        Stimuli: {1}
        """.format(str(self.id),
                   [stimulus.id for stimulus in self.stimuli])

    def set_factor(self, name, value):
        """Set a factor for the trial.

        Parameters
        ----------
        name : str
            factor name
        value : str or numeric
            factor value

        """

        if type(value) in [types.StringType, types.IntType, types.LongType,
                           types.FloatType]:
            self._factors[name] = value
        else:
            message = "Factor values or factor conditions must to be a " + \
                    "string or a numeric (i.e. float or integer).\n " + \
                    "{0} is not allowed.".format(type(value))
            raise TypeError(message)

    def get_factor(self, name):
        """Get a factor of the trial.

        Parameters
        ----------
        name : str
            factor name

        Returns
        -------
        factor_val : str or numeric

        """

        try:
            rtn = self._factors[name]
        except:
            rtn = None
        return rtn

    @property
    def factor_dict(self):
        """The dictionary with all factors of the trial."""

        return self._factors

    def clear_factors(self):
        """Clear all factors."""

        self._factors = {}

    @property
    def factor_names(self):
        """Getter for factors names."""

        return self._factors.keys()

    @property
    def factors_as_text(self):
        """Return all factor names and values as csv string line"""
        all_factors = ""
        for f in self.factor_names:
            all_factors = all_factors + "{0}={1}, ".format(f, \
                                self.get_factor(f))
        return all_factors

    def add_stimulus(self, stimulus):
        """Add a stimulus to the trial.

        Notes
        -----
        This will add references to stimuli, not copies!

        Parameters
        ----------
        stimulus : expyriment stimulus
            stimulus to add (expyriment.stimuli.* object)

        """

        self._stimuli.append(stimulus)

        expyriment._active_exp._event_file_log(
                "Trial,stimulus added,{0},{1}".format(self.id, stimulus.id), 2)

    def remove_stimulus(self, position):
        """Remove stimulus from trial.

        Parameters
        ----------
        position : int
            position of the stimulus

        """

        stimulus = self._stimuli.pop(position)

        expyriment._active_exp._event_file_log(
            "Trial,stimulus removed,{0},{1}".format(self.id, stimulus.id), 2)

    def order_stimuli(self, order):
        """Order the stimuli.

        Parameters
        ----------
        order : list
            list with the new order of positions

        """

        if not len(order) == len(self._stimuli):
            raise ValueError("Given order has wrong number of items!")
        stimuli_new = []
        for position in order:
            stimuli_new.append(self._stimuli[position])
        self._stimuli = stimuli_new

    def clear_stimuli(self):
        """Clear the stimuli."""

        self._stimuli = []
        expyriment._active_exp._event_file_log("Trial,stimuli cleared", 2)

    def swap_stimuli(self, position1, position2):
        """Swap two stimuli.

        Parameters
        ----------
        position1 : int
            position of first stimulus
        position2 : int
            position of second stimulus

        """

        if position1 < len(self._stimuli) and position2 < len(self._stimuli):
            self._stimuli[position1], self._stimuli[position2] = \
                    self._stimuli[position2], self._stimuli[position1]
            return True
        else:
            return False

    def shuffle_stimuli(self):
        """Shuffle all stimuli."""

        randomize.shuffle_list(self.stimuli)

    def sort_stimuli(self):
        """Sort the stimuli according to their IDs from low to high."""

        stimuli_new = []
        id_list = [x.id for x in self._stimuli]
        id_list.sort()
        for _id in id_list:
            position = [i for i, x in enumerate(self._stimuli) \
                         if x.id == _id][0]
            stimuli_new.append(self._stimuli[position])
        self._stimuli = stimuli_new

    def find_stimulus(self, id):
        """Find the positions of a stimulus.

        Parameters
        ----------
        id : int
            stimulus id to look for

        Returns
        -------
        pos : int
            positions as a list or None if not in stimuli list

        """

        positions = [i for i, x in enumerate(self._stimuli) if x.id == id]
        if positions:
            return positions

    def copy(self):
        """Return a copy of the trial."""

        stimlist = []
        for stim in self._stimuli:
            stimlist.append(stim)
        self._stimuli = None
        rtn = deepcopy(self)
        self._stimuli = rtn._stimuli = stimlist
        return rtn

    def preload_stimuli(self):
        """Preload all stimuli in trial.

        Returns
        -------
        time : int
            time it took to execute this method in ms

        """

        start = Clock._cpu_time()
        for stim in self._stimuli:
            stim.preload()
        return int((Clock._cpu_time() - start) * 1000)

    def unload_stimuli(self, keep_surface=False):
        """Unload all stimuli in trial.

        Parameters
        ----------
        keep_surface : bool, optional
            keep the surface after unloading (default = False)

        Returns
        -------
        time : int
            time it took to execute this method in ms

        """

        start = Clock._cpu_time()
        for stim in self._stimuli:
            stim.unload(keep_surface=keep_surface)
        return int((Clock._cpu_time() - start) * 1000)