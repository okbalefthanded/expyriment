"""
The control._experiment_control module of expyriment.

"""

__author__ = 'Florian Krause <florian@expyriment.org>, \
Oliver Lindemann <oliver@expyriment.org>'
__version__ = ''
__revision__ = ''
__date__ = ''

import sys

import pygame
try:
    import android
except ImportError:
    android = None
try:
    import android.mixer as mixer
except ImportError:
    import pygame.mixer as mixer

import defaults
import expyriment
from expyriment import design, stimuli, misc
from expyriment.io import  DataFile, EventFile, TextInput, Keyboard
from expyriment.io import _keyboard
from expyriment.io._screen import Screen
from _miscellaneous import _set_stdout_logging, is_idle_running


def start(experiment=None, auto_create_subject_id=None):
    """Start an experiment.

    This starts an experiment defined by 'experiment' and asks for the subject
    number. When the subject number is entered and confirmed by ENTER, a data
    file is created.
    Eventually, "Ready" will be shown on the screen and the method waits for
    ENTER to be pressed.

    After experiment start the following additional properties are available:

    * experiment.subject -- the current subject id
    * experiment.data    -- the main data file

    Parameters
    ----------
    experiment : design.Experiment, optional (DEPRECATED)
        Don't use this parameter, it only exists to keep backward compatibility.
    auto_create_subject_id : bool
        if true new subject id will be created automatically

    Returns
    -------
    exp : design.Experiment
        The started experiment will be returned.

    """

    if experiment is None:
        experiment = expyriment._active_exp
    if experiment != expyriment._active_exp:
        raise Exception("Experiment is not the currently initialized " +
                        "experiment!")
    if experiment.is_started:
        raise Exception("Experiment is already started!")
    if auto_create_subject_id is None:
        auto_create_subject_id = defaults.auto_create_subject_id

    experiment._is_started = True
    # temporarily switch off log_level
    old_logging = experiment.log_level
    experiment.set_log_level(0)
    screen_colour = experiment.screen.colour
    experiment._screen.colour = [0, 0, 0]
    default_number = DataFile.get_next_subject_number()
    if not auto_create_subject_id:
        if android is not None:
            position = (0, 200)
        else:
            position = None
        while True:
            ask_for_subject = TextInput(message="Subject Number:",
                            position=position,
                            message_colour=misc.constants.C_EXPYRIMENT_PURPLE,
                            message_text_size=24,
                            user_text_colour=misc.constants.C_EXPYRIMENT_ORANGE,
                            user_text_size=20,
                            background_colour=(0, 0, 0),
                            frame_colour=(70, 70, 70),
                            ascii_filter=misc.constants.K_ALL_DIGITS)
            subject_id = ask_for_subject.get(repr(default_number))
            try:
                experiment._subject = int(subject_id)
                break
            except:
                pass

    else:
        experiment._subject = default_number

    experiment.screen.clear()
    experiment.screen.update()
    experiment._data = DataFile(additional_suffix=experiment.filename_suffix)
    experiment.data.add_variable_names(experiment.data_variable_names)
    for txt in experiment.experiment_info:
        experiment.data.add_experiment_info(txt)
    for line in experiment.__str__().splitlines():
        experiment.data.add_experiment_info(line)

    for f in experiment.bws_factor_names:
            experiment.data.add_subject_info("{0} = {1}".format(f,
                            experiment.get_permuted_bws_factor_condition(f)))

    if experiment.events is not None:
        experiment.events._time_stamp = experiment.data._time_stamp
        experiment.events.rename(experiment.events.standard_file_name)

    number = defaults.initialize_delay - int(experiment.clock.time / 1000)
    if number > 0:
        text = stimuli.TextLine("Initializing, please wait...",
                                text_size=24,
                                text_colour=(160, 70, 250),
                                position=(0, 0))
        stimuli._stimulus.Stimulus._id_counter -= 1
        text.present()
        text.present()  # for flipping with double buffer
        text.present()  # for flipping with tripple buffer
    while number > 0:
        counter = stimuli.TextLine("{num:02d}".format(num=number),
                               text_font='Monospace',
                               text_size=18,
                               text_bold=True,
                               text_colour=misc.constants.C_EXPYRIMENT_ORANGE,
                               position=(0, -50),
                               background_colour=(0, 0, 0))

        stimuli._stimulus.Stimulus._id_counter -= 1
        counter.present(clear=False)
        number -= 1
        key = experiment.keyboard.wait(pygame.K_ESCAPE, duration=1000,
                     check_for_control_keys=False)
        if key[0] is not None:
            break

    stimuli.TextLine("Ready", text_size=24,
                     text_colour=misc.constants.C_EXPYRIMENT_ORANGE).present()
    stimuli._stimulus.Stimulus._id_counter -= 1
    experiment.keyboard.wait()
    experiment.set_log_level(old_logging)
    experiment._screen.colour = screen_colour
    experiment.log_design_to_event_file()
    experiment._event_file_log("Experiment,started")
    return experiment


def pause():
    """Pause a running experiment.

    This will show a pause screen and waits for ENTER to be pressed to
    continue.

    """

    if not expyriment._active_exp.is_initialized:
        raise Exception("Experiment is not initialized!")
    experiment = expyriment._active_exp
    experiment._event_file_log("Experiment,paused")
    screen_colour = experiment.screen.colour
    experiment._screen.colour = [0, 0, 0]
    old_logging = experiment.log_level
    experiment.set_log_level(0)
    stimuli.TextLine("Paused", text_colour=misc.constants.C_EXPYRIMENT_ORANGE,
                    text_size=24).present()
    experiment.set_log_level(old_logging)
    experiment._screen.colour = screen_colour
    stimuli._stimulus.Stimulus._id_counter -= 1
    misc.Clock().wait(200)
    key = Keyboard().wait(pygame.K_RETURN)
    experiment._event_file_log("Experiment,resumed")
    return key


def end(goodbye_text=None, goodbye_delay=None, confirmation=False,
        fast_quit=None, system_exit=False):
    """End expyriment.

    Parameters
    ----------
    goodbye_text  : str, obligatory
        text to present on the screen when quitting
    goodbye_delay : int, optional
        period to show the goodbye_text
    confirmation : bool, optional
        ask for confirmation (default = False)
    fast_quit : bool, optional
        quit faster by hiding the screen before actually quitting
        (default = None)
    system_exit : bool, optional
        call Python's sys.exit() method when ending expyriment (default = False)

    Returns
    -------
    out : bool
        True if Expyriment (incl. Pygame) has been quit.

    """

    if not expyriment._active_exp.is_initialized:
        pygame.quit()
        if system_exit:
            sys.exit()
        return True
    experiment = expyriment._active_exp
    if confirmation:
        experiment._event_file_log("Experiment,paused")
        screen_colour = experiment.screen.colour
        experiment._screen.colour = [0, 0, 0]
        stimuli.TextLine("Quitting Experiment? (y/n)",
                         text_colour=misc.constants.C_EXPYRIMENT_ORANGE,
                         text_size=24).present()
        stimuli._stimulus.Stimulus._id_counter -= 1
        char = Keyboard().wait_char(["y", "n"], check_for_control_keys=False)
        if char[0] == "n":
            experiment._screen.colour = screen_colour
            experiment._event_file_log("Experiment,resumed")
            return False
    experiment._event_file_log("Experiment,ended")
    if goodbye_text is None:
        goodbye_text = defaults.goodbye_text
    if goodbye_delay is None:
        goodbye_delay = defaults.goodbye_delay
    if experiment.events is not None:
        experiment.events.save()
    if experiment.data is not None:
        experiment.data.save()
    if fast_quit is None:
        fast_quit = defaults.fast_quit
    if fast_quit and experiment.is_started:
        if  experiment.screen.window_mode:
            pygame.display.set_mode(experiment.screen._window_size)
            pygame.display.iconify()

    experiment._screen.colour = [0, 0, 0]
    stimuli.TextLine(goodbye_text,
                     text_colour=misc.constants.C_EXPYRIMENT_PURPLE,
                     text_size=24).present()
    stimuli._stimulus.Stimulus._id_counter -= 1
    if not fast_quit:
        misc.Clock().wait(goodbye_delay)
    expyriment._active_exp = design.Experiment("None")
    pygame.quit()
    return True


def initialize(experiment=None):
    """Initialize an experiment.

    This initializes an experiment defined by 'experiment' as well as the
    underlying expyriment system. If 'experiment' is None, a new Experiment
    object will be created and returned. Furthermore, a screen, a clock, a
    keyboard and a event file are created and added to the experiment. The
    initialization screen is shown for a short delay to ensure that Python
    is fully initialized and time accurate. Afterwards, "Preparing
    experiment..." is presented on the screen.

    After experiment initialize the following additional properties are
    available:

    - experiment.screen   -- the current screen
    - experiment.clock    -- the main clock
    - experiment.keyboard -- the main keyboard
    - experiment.event    -- the main event file

    Parameters
    ----------
    experiment : design.Experiment, optional
        the experiment to initialize

    Returns
    -------
    exp : design.Experiment
        initialized experiment

    """

    if experiment is None:
        experiment = design.Experiment()
    stdout_logging = defaults.stdout_logging
    expyriment._active_exp = experiment
    experiment._log_level = 0  # switch off for the first screens

    _keyboard.quit_key = defaults.quit_key
    _keyboard.pause_key = defaults.pause_key
    _keyboard.end_function = end
    _keyboard.pause_function = pause

    mixer.pre_init(defaults.audiosystem_sample_rate,
                   defaults.audiosystem_bit_depth,
                   defaults.audiosystem_channels,
                   defaults.audiosystem_buffer_size)
    if defaults.audiosystem_autostart:
        mixer.init()
        mixer.init()  # Needed on some systems

    experiment._clock = misc.Clock()
    experiment._screen = Screen((0, 0, 0), defaults.open_gl,
                                defaults.window_mode, defaults.window_size)
    # Hack for IDLE: quit pygame and call atexit functions when crashing
    if is_idle_running() and sys.argv[0] != "":
        try:
            import idlelib.run
            def wrap(orig_func):
                def newfunc(*a, **kw):
                    pygame.quit()
                    import atexit
                    atexit._run_exitfuncs()
                    idlelib.run.flush_stdout = orig_func
                    return orig_func(*a, **kw)
                return newfunc
            idlelib.run.flush_stdout = wrap(idlelib.run.flush_stdout)
        except ImportError:
            pass
    experiment._data = None
    experiment._subject = None
    experiment._is_initialized = True  # required before EventFile
    if defaults.event_logging > 0:
        experiment._events = EventFile(additional_suffix=experiment.filename_suffix,
                                       time_stamp=True)
        if stdout_logging:
            _set_stdout_logging(experiment._events)
    else:
        experiment._events = None
    experiment._keyboard = Keyboard()

    logo = stimuli.Picture(misc.constants.EXPYRIMENT_LOGO_FILE,
                           position=(0, 100))
    logo.scale((0.7, 0.7))
    text = stimuli.TextLine("Version {0}".format(expyriment.get_version()),
                            text_size=14,
                            text_colour=misc.constants.C_EXPYRIMENT_ORANGE,
                            background_colour=(0, 0, 0),
                            position=(0, 40))
    canvas = stimuli.Canvas((600, 300), colour=(0, 0, 0))
    canvas2 = stimuli.Canvas((600, 300), colour=(0, 0, 0))
    logo.plot(canvas)
    text.plot(canvas)
    canvas.preload(True)
    canvas._set_surface(canvas._get_surface().convert())
    start = experiment.clock.time
    r = [x for x in range(256) if x % 5 == 0]
    stopped = False
    if defaults.initialize_delay > 0:
        for x in r:
            canvas._get_surface().set_alpha(x)
            canvas2.clear_surface()
            canvas.plot(canvas2)
            canvas2.present()
            experiment.clock.wait(1)
            key = experiment.keyboard.check(pygame.K_ESCAPE,
                                      check_for_control_keys=False)
            if key is not None:
                stopped = True
                break
        duration = experiment.clock.time - start
        if duration < 2000 and not stopped:
            start = experiment.clock.time
            while experiment.clock.time - start < 2000:
                key = experiment.keyboard.check(pygame.K_ESCAPE,
                                          check_for_control_keys=False)
                if key is not None:
                    stopped = True
                    break
        r = [x for x in range(256)[::-1] if x % 5 == 0]
        if not stopped:
            for x in r:
                canvas._get_surface().set_alpha(x)
                canvas2.clear_surface()
                canvas.plot(canvas2)
                canvas2.present()
                experiment.clock.wait(1)
                key = experiment.keyboard.check(pygame.K_ESCAPE,
                                          check_for_control_keys=False)
                if key is not None:
                    break
    stimuli.TextLine("Preparing experiment...", text_size=24,
                     text_colour=misc.constants.C_EXPYRIMENT_PURPLE).present()
    experiment._screen.colour = experiment.background_colour
    experiment.set_log_level(defaults.event_logging)
    stimuli._stimulus.Stimulus._id_counter = 0
    return experiment