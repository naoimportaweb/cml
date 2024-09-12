# Copyright (C) 2013 Riverbank Computing Limited.
# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

"""PySide6 port of the widgets/mainwindows/mdi example from Qt v5.x, originating from PyQt"""
import json;
import os, sys, inspect;
CURRENTDIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())));
sys.path.append(CURRENTDIR);
sys.path.append( os.path.dirname( CURRENTDIR ));

from classlib.connectobject import ConnectObject;

from classlib.user import User;

user = User("maria", "")
print(user.session());



