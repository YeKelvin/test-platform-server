#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : controller.py
# @Time    : 2019/11/14 9:50
# @Author  : Kelvin.Ye
from flask import Blueprint

from app.utils.log_util import get_logger


log = get_logger(__name__)

# TODO: prefix修改为 /rest/api/{v+版本号}/{module}/{resource}
# TODO: 响应报文的Header添加名为 API-Version 的头，值为 day-month-year 格式的日期
blueprint = Blueprint('file', __name__, url_prefix='/file')


@blueprint.post('/upload')
def upload():
    pass


@blueprint.get('/download')
def download():
    pass
