#!/usr/bin/python3
import socket, signal, sys, time, threading, json;
import traceback, os, inspect, uuid;
import importlib

from datetime import datetime;

class Dynamic_import:
    def execute(self, client, module_name, class_name, function_name, parameters):
        ClassBuffer = getattr(importlib.import_module( module_name ), class_name)
        instance = ClassBuffer()
        retorno_metodo = getattr(instance, function_name)( client, parameters );
        return retorno_metodo;
                

class WebServer(object):
    def __init__(self, port=8080):
        self.host = socket.gethostname().split('.')[0];
        self.host = "0.0.0.0";
        self.port = port;
        self.content_dir = 'web';

    def start(self):
        try:
            self.__start();
        except KeyboardInterrupt:
            sys.exit(1);
        except:
            traceback.print_exc();
            self.shutdown();

    def __start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
        try:
            self.socket.bind((self.host, self.port));
        except Exception as e:
            print("Error: Could not bind to port {port}".format(port=self.port));
            self.shutdown();
            sys.exit(1);
        self.__listen() # Start listening for connections

    def shutdown(self):
        try:
            print("Shutting down server");
            self.socket.shutdown(socket.SHUT_RDWR);
        except Exception as e:
            pass # Pass if socket is already closed

    def __listen(self):
        self.socket.listen(500);
        while True:
            try:
                (client, address) = self.socket.accept();
                threading.Thread(target=self._handle_client, args=(client, address)).start();
            except KeyboardInterrupt:
                sys.exit(1);
            except:
                traceback.print_exc();

    def _handle_client(self, client, address):
        retorno = "HTTP/1.1 200 OK\r\nContent-Type: application/text; charset=UTF-8\r\nConnection: keep-alive\r\nContent-Length: {LENGTH} \r\n\r\n"
        with client:
            # Ler o cabeçalho do HTTP
            head = "";
            while True:
                data = client.recv(1);
                if not data: break
                head += data.decode('utf-8');
                if head[-4:] == "\r\n\r\n":
                    break;
            
            body_size = 0;
            head_lines = head.split("\r\n");
            for line in head_lines:
                if line.lower()[:len("Content-Length")] == "content-length":
                    body_size = int( line.split(":")[1].strip() );
            # Ler o Body do HTTP
            body = "";
            if body_size > 0:
                print("Ler o corpo");
                body = client.recv( body_size ).decode("utf-8");

            print(head, body);
            generics = Dynamic_import();
            o_que_vou_responder = generics.execute(client, );
            client.sendall((retorno.replace( "{LENGTH}" , str(len(o_que_vou_responder)) ) + o_que_vou_responder ).encode("utf-8"))


m = WebServer(8080);
m.start();
