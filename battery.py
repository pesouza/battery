#!/usr/bin/env python
import curses, argparse, sys, time, threading, itertools

import pygame

import cui
from utils import load_banks


VERSION = 0.3
# That's all what MaKeyMaKey has in stock setting, except 'SPC' and 'w'
AVAILABLE_KEYS = 'LEFT RIGHT DOWN UP a s d f g h j'.split()
KEYS = dict(
    [(getattr(curses, 'KEY_%s' % key, ord(key[0])), key) for key in AVAILABLE_KEYS])


def parse_args():
    parser = argparse.ArgumentParser('Battery - a simple CLI & headless rompler')
    parser.add_argument('-b', '--bank-kit', action='store', dest='bank_kit', default='default')
    return parser.parse_args()

def init_mixer():
    # We need to init mixer before pygame initializations, smaller buffer should avoid lags
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.init()
    pygame.mixer.set_num_channels(8 * len(KEYS)) # Get 8 channels for each key

class LoopThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.loop = []
        self.running = False

    def run(self):
        try:
            self.loop.next()[1].play()
        except StopIteration:
            return

        self.running = True
        while self.running:
            sleep_time, sample = self.loop.next()
            time.sleep(sleep_time)
            sample.play()

    def stop(self):
        self.running = False



if __name__ == "__main__":
    init_mixer()
    args = parse_args()

    banks_iter = load_banks(args.bank_kit)
    if not banks_iter:
        sys.exit('Can\'t load bank kit file "%s"' % args.bank_kit)

    bank_desc, bank_samples, bank_nr = banks_iter.next()

    cui = cui.CUI(VERSION)
    cui.show_bank(bank_desc, bank_nr)

    reverse, loop_recording, loops = False, False, []
    t_prev, current_loop = 0, None

    while True:
        event = cui.screen.getch()
        t = time.time()

        if event in (ord('q'), 27): #q or ESC
            break

        elif event == ord(' '): # switch bank on SPACE
            bank_desc, bank_samples, bank_nr = banks_iter.next()
            cui.show_bank(bank_desc, bank_nr)
            continue

        elif event == ord('r'): # start/stop recording new loop
            if loop_recording is False: #start new loop
                current_loop = LoopThread()
                current_loop.daemon = True
                loops.append(current_loop)
            else:
                try:
                    dummy = current_loop.loop[-1]
                except IndexError:
                    del(loops[-1])
                    loop_recording = not loop_recording
                    current_loop = None
                    cui.tray_msg('recording: %s' % ('on' if loop_recording else 'off'), style=curses.A_BOLD)
                    continue

                # set the wait "before first sample" to time between last "sound" and "end recording"
                current_loop.loop[0][0] = t - t_prev

                current_loop.loop = itertools.cycle(current_loop.loop)
                current_loop.start()
            loop_recording = not loop_recording
            cui.tray_msg('recording: %s' % ('on' if loop_recording else 'off'), style=curses.A_BOLD)

        elif event == ord('p'): # stop & delete last loop
            try:
                loops[-1].stop()
                del(loops[-1])
                cui.tray_msg('last loop stopped & deleted', style=curses.A_BOLD)
            except IndexError:
                loops = []

        elif event == ord('w'):
            reverse = not reverse
            cui.tray_msg('reverse mode: %s' % ('on' if reverse else 'off'), style=curses.A_BOLD)

        try:
            key = KEYS[event]
            try:
                sample = bank_samples[key][int(reverse)]
                sample.play()
                if loop_recording:
                    current_loop.loop.append([t-t_prev, sample])
                t_prev = t
            except KeyError:
                cui.tray_msg('No sample defined for "%s" key\n' % key, row=1, style=curses.A_DIM)
        except KeyError:
            pass

    # This should somehow restore terminal back, but it doesn't work all the time.
    # Call "reset" in your shell if you need to
    curses.endwin()
    sys.exit(0)
