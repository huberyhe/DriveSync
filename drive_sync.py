#!/usr/bin/env python
import os
import sys
import time
import logging
import shutil
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler

path_one = "/mnt/e/OCOD/test_d1"
path_another = "/mnt/e/OCOD/test_d2"
paths = [path_one + '/d1', path_one + '/d2', path_one + '/d3', path_another + '/d1', path_another + '/d2', path_another + '/d3']
file_in_handler = {}
HANDLER_WAIT = 10

def get_another_path(src_path):
    if path_one in src_path:
        return src_path.replace(path_one, path_another)
    elif path_another in src_path:
        return src_path.replace(path_another, path_one)
    else:
        return None

class SyncHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        src_path = event.src_path
        event_type = event.event_type
        is_directory = event.is_directory
        if is_directory: return
        if not is_directory and (src_path not in file_in_handler or time.time() - file_in_handler[src_path] > HANDLER_WAIT):
            dst_path = get_another_path(src_path)
            logging.info("%s %s handle" % (src_path, event_type))
            time.sleep(HANDLER_WAIT) #延迟处理
            try: 
                if event_type in ['created', 'modified']:
                    dst_path_dir = os.path.dirname(dst_path)
                    if not os.path.exists(dst_path_dir):
                        os.makedirs(dst_path_dir)
                    shutil.copy2(src_path, dst_path)
                elif event_type in ['deleted']:
                    if os.path.exists(dst_path): os.remove(dst_path)
                else:
                    pass
            except Exception as e:
                logging.error('Failed:%s' % e.message)
                pass
            file_in_handler[dst_path] = file_in_handler[src_path] = time.time()
        else:
            logging.info("%s %s pass" % (src_path, event_type))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    event_handler = SyncHandler()
    observers = []
    observer = Observer()
    for path in paths:
        observer.schedule(event_handler, path, recursive=True)
        observers.append(observer)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for o in observers:
            o.unschedule_all
            o.stop
    #     observer.stop()
    # observer.join()
    for o in observers:
        o.join
