#!/usr/bin/env python
import os
import sys
import time
import logging
import shutil
import filecmp
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
from multiprocessing import Process
import threading,Queue

path_one = "/mnt/e/OCOD/test_d1"
path_another = "/mnt/e/OCOD/test_d2"
paths = [path_one + '/d1', path_one + '/d2', path_one + '/d3', path_another + '/d1', path_another + '/d2', path_another + '/d3']
file_handler_stat = {}
HANDLER_WAIT = 10

def get_another_path(src_path):
    if path_one in src_path:
        return src_path.replace(path_one, path_another)
    elif path_another in src_path:
        return src_path.replace(path_another, path_one)
    else:
        return None

def add_handle_queue(event):
    src_path = event.src_path
    event_type = event.event_type
    is_directory = event.is_directory
    if is_directory: return
    if not is_directory and (src_path not in file_handler_stat or time.time() - file_handler_stat[src_path] > HANDLER_WAIT):
        dst_path = get_another_path(src_path)
        logging.info("%s %s handle" % (src_path, event_type))
        time.sleep(HANDLER_WAIT) #延迟处理
        try:
            if event_type in ['created']:
                dst_path_dir = os.path.dirname(dst_path)
                if not os.path.exists(dst_path_dir):
                    os.makedirs(dst_path_dir)
                shutil.copy2(src_path, dst_path)
            elif event_type in ['modified']:
                if not filecmp.cmp(src_path, dst_path):
                    shutil.copy2(src_path, dst_path)
            elif event_type in ['deleted']:
                if not os.path.exists(src_path) and os.path.exists(dst_path):
                    os.remove(dst_path)
            else:
                pass
        except Exception as e:
            logging.error('Failed:%s' % e.message)
            pass
        file_handler_stat[dst_path] = file_handler_stat[src_path] = time.time()
    else:
        logging.info("%s %s pass" % (src_path, event_type))


class SyncHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        add_handle_queue(event)

def event_handler_p():
    '''
    对文件修改事件的处理进程，使用多个线程进行处理
    '''
    

def file_watchdog_p():
    '''
    对文件夹监听，生成事件的
    '''
    pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    #启动一个进程，用于处理事件队列
    q = Queue.Queue()
    p = Process(target=event_handler_p, args=(q,))
    p.start()
    #启动文件看门狗
    event_handler = SyncHandler()
    observers = []
    observer = Observer()
    for path in paths:
        observer.schedule(event_handler, path, recursive=True)
        observers.append(observer)
    observer.start()

    #接收到推出指令，关闭看门狗和事件处理进程
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
    p.join()