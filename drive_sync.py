#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
import shutil
import filecmp
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
from multiprocessing import Process,Queue
import threading

path_one = "/mnt/e/OCOD/test_d1"
path_another = "/mnt/e/OCOD/test_d2"
paths = [path_one + '/d1', path_one + '/d2', path_one + '/d3', path_another + '/d1', path_another + '/d2', path_another + '/d3']
file_handler_stat = {}
HANDLER_WAIT = 10
WORKER_NUM = 3

def get_another_path(src_path):
    if path_one in src_path:
        return src_path.replace(path_one, path_another)
    elif path_another in src_path:
        return src_path.replace(path_another, path_one)
    else:
        return None

def handle_event_queue(event):
    src_path = event.src_path
    event_type = event.event_type
    is_directory = event.is_directory
    if is_directory: return
    if not is_directory and (src_path not in file_handler_stat or time.time() - file_handler_stat[src_path] > HANDLER_WAIT):
        dst_path = get_another_path(src_path)
        logging.info("%s %s handle" % (src_path, event_type))
        #延迟处理
        time.sleep(HANDLER_WAIT)
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
    def __init__(self, q):
        FileSystemEventHandler.__init__(self)
        self.e_queue = q

    def on_any_event(self, event):
        logging.info('queue put')
        self.e_queue.put(event)

def event_handler_t(nloop, event):
    '''
    对文件修改事件的处理线程
    '''
    logging.info('in event_handler_t %d' % nloop)
    handle_event_queue(event)

def event_handler_p(q):
    '''
    对文件修改事件的处理进程，使用多个线程进行处理
    '''
    workers = []
    nloops = range(WORKER_NUM)
    for i in nloops:
        worker = threading.Thread(target=event_handler_t, args=(i, q,))
        # worker.setDaemon(True)
        workers.append(worker)

    for i in nloops:
        workers[i].start

    while True:
        if not q.empty():
            event = q.get()
            logging.info('queue get')
            handle_event_queue(event)
        else:
            time.sleep(1)
    
    for i in nloops:
        workers[i].join()

def file_watchdog_p():
    '''
    对文件夹监听，生成事件的
    '''
    pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(funcName)s:%(lineno)d - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    #启动一个进程，用于处理事件队列
    q = Queue()
    p = Process(target=event_handler_p, args=(q,))
    p.start()
    #启动文件看门狗
    event_handler = SyncHandler(q)
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