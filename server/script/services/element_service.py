#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : element_service
# @Time    : 2020/3/13 16:58
# @Author  : Kelvin.Ye
from server.librarys.number_generator import generate_no
from server.extensions import db
from server.librarys.decorators.service import http_service
from server.librarys.decorators.transaction import db_transaction
from server.librarys.exception import ServiceError
from server.librarys.request import RequestDTO
from server.librarys.verify import Verify
from server.script.model import TTestElement, TElementProperty, TElementChildRel, TWorkspaceCollectionRel, TWorkspace
from server.script.services.element_helper import ElementStatus
from server.utils.log_util import get_logger

log = get_logger(__name__)


@http_service
def query_element_list(req: RequestDTO):
    # 查询条件
    conditions = [TTestElement.DEL_STATE == 0]

    if req.attr.elementNo:
        conditions.append(TTestElement.ELEMENT_NO == req.attr.elementNo)
    if req.attr.elementName:
        conditions.append(TTestElement.ELEMENT_NAME.like(f'%{req.attr.elementName}%'))
    if req.attr.elementComments:
        conditions.append(TTestElement.ELEMENT_COMMENTS.like(f'%{req.attr.elementComments}%'))
    if req.attr.elementType:
        conditions.append(TTestElement.ELEMENT_TYPE.like(f'%{req.attr.elementType}%'))
    if req.attr.enabled:
        conditions.append(TTestElement.ENABLED.like(f'%{req.attr.enabled}%'))

    if req.attr.workspaceNo:
        conditions.append(TWorkspaceCollectionRel.DEL_STATE == 0)
        conditions.append(TWorkspaceCollectionRel.COLLECTION_NO == TTestElement.ELEMENT_NO)
        conditions.append(TWorkspaceCollectionRel.WORKSPACE_NO.like(f'%{req.attr.workspaceNo}%'))
    if req.attr.workspaceName:
        conditions.append(TWorkspace.DEL_STATE == 0)
        conditions.append(TWorkspaceCollectionRel.DEL_STATE == 0)
        conditions.append(TWorkspaceCollectionRel.COLLECTION_NO == TTestElement.ELEMENT_NO)
        conditions.append(TWorkspaceCollectionRel.WORKSPACE_NO == TWorkspace.WORKSPACE_NO)
        conditions.append(TWorkspace.WORKSPACE_NAME.like(f'%{req.attr.workspaceName}%'))

    pagination = db.session.query(
        TTestElement.ELEMENT_NO,
        TTestElement.ELEMENT_NAME,
        TTestElement.ELEMENT_COMMENTS,
        TTestElement.ELEMENT_TYPE,
        TTestElement.ENABLED
    ).filter(*conditions).order_by(TTestElement.CREATED_TIME.desc()).paginate(req.attr.page, req.attr.pageSize)

    # 组装数据
    data_set = []
    for item in pagination.items:
        data_set.append({
            'elementNo': item.ELEMENT_NO,
            'elementName': item.ELEMENT_NAME,
            'elementType': item.ELEMENT_TYPE,
            'enabled': item.ENABLED
        })
    return {'dataSet': data_set, 'totalSize': pagination.total}


@http_service
def query_element_all(req: RequestDTO):
    # 查询条件
    conditions = [
        TTestElement.DEL_STATE == 0,
        TWorkspaceCollectionRel.DEL_STATE == 0,
        TWorkspaceCollectionRel.COLLECTION_NO == TTestElement.ELEMENT_NO
    ]

    if req.attr.workspaceNo:
        conditions.append(TWorkspaceCollectionRel.WORKSPACE_NO.like(f'%{req.attr.workspaceNo}%'))
    if req.attr.elementType:
        conditions.append(TTestElement.ELEMENT_TYPE.like(f'%{req.attr.elementType}%'))
    if req.attr.enabled:
        conditions.append(TTestElement.ENABLED.like(f'%{req.attr.enabled}%'))

    items = db.session.query(
        TTestElement.ELEMENT_NO,
        TTestElement.ELEMENT_NAME,
        TTestElement.ELEMENT_COMMENTS,
        TTestElement.ELEMENT_TYPE,
        TTestElement.ENABLED
    ).filter(*conditions).order_by(TTestElement.CREATED_TIME.desc()).all()

    result = []
    for item in items:
        result.append({
            'elementNo': item.ELEMENT_NO,
            'elementName': item.ELEMENT_NAME,
            'elementType': item.ELEMENT_TYPE,
            'enabled': item.ENABLED
        })
    return result


@http_service
def query_element_info(req: RequestDTO):
    element = TTestElement.query_by(ELEMENT_NO=req.attr.elementNo).first()
    Verify.not_empty(element, '测试元素不存在')

    el_props = TElementProperty.query_by(ELEMENT_NO=req.attr.elementNo).all()
    has_children = TElementChildRel.query_by(PARENT_NO=req.attr.elementNo).count() > 0
    propertys = {}
    for prop in el_props:
        propertys[prop.PROPERTY_NAME] = prop.PROPERTY_VALUE

    return {
        'elementNo': element.ELEMENT_NO,
        'elementName': element.ELEMENT_NAME,
        'elementComments': element.ELEMENT_COMMENTS,
        'elementType': element.ELEMENT_TYPE,
        'enabled': element.ENABLED,
        'propertys': propertys,
        'hasChildren': has_children
    }


@http_service
def query_element_children(req: RequestDTO):
    return depth_query_element_children(req.attr.elementNo, req.attr.depth)


def depth_query_element_children(elementNo, depth):
    result = []
    element_children_rel = TElementChildRel.query_by(PARENT_NO=elementNo).all()
    if not element_children_rel:
        return result

    # 根据 child_order排序
    element_children_rel.sort(key=lambda k: k.CHILD_ORDER)
    for element_child_rel in element_children_rel:
        element = TTestElement.query_by(ELEMENT_NO=element_child_rel.CHILD_NO).first()
        if element:
            children = depth and query_element_children(element_child_rel.CHILD_NO, depth) or []
            result.append({
                'elementNo': element.ELEMENT_NO,
                'elementName': element.ELEMENT_NAME,
                'elementType': element.ELEMENT_TYPE,
                'enabled': element.ENABLED,
                'order': element_child_rel.CHILD_ORDER,
                'children': children
            })
    return result


@http_service
@db_transaction
def create_element(req: RequestDTO):
    element_no = create_element_with_transaction(
        element_name=req.attr.elementName,
        element_comments=req.attr.elementComments,
        element_type=req.attr.elementType,
        propertys=req.attr.propertys,
        children=req.attr.children
    )

    if req.attr.workspaceNo:
        workspace = TWorkspace.query_by(WORKSPACE_NO=req.attr.workspaceNo).first()
        Verify.not_empty(workspace, '测试项目不存在')

        TWorkspaceCollectionRel.create(
            commit=False,
            WORKSPACE_NO=req.attr.workspaceNo,
            COLLECTION_NO=element_no
        )

    return {'elementNo': element_no}


@http_service
@db_transaction
def modify_element(req: RequestDTO):
    modify_element_with_transaction(
        element_no=req.attr.elementNo,
        element_name=req.attr.elementName,
        element_comments=req.attr.elementComments,
        element_type=req.attr.elementType,
        propertys=req.attr.propertys,
        children=req.attr.children
    )
    return None


@http_service
@db_transaction
def delete_element(req: RequestDTO):
    return delete_element_with_transaction(element_no=req.attr.elementNo)


@http_service
def enable_element(req: RequestDTO):
    element = TTestElement.query_by(ELEMENT_NO=req.attr.elementNo).first()
    Verify.not_empty(element, '测试元素不存在')

    element.enabled = ElementStatus.ENABLE.value
    element.save()
    return None


@http_service
def disable_element(req: RequestDTO):
    element = TTestElement.query_by(ELEMENT_NO=req.attr.elementNo).first()
    Verify.not_empty(element, '测试元素不存在')

    element.enabled = ElementStatus.DISABLE.value
    element.save()
    return None


@http_service
def add_element_property(req: RequestDTO):
    el_prop = TElementProperty.query_by(ELEMENT_NO=req.attr.elementNo, PROPERTY_NAME=req.attr.propertyName).first()
    Verify.empty(el_prop, '元素属性已存在')

    TElementProperty.create(
        ELEMENT_NO=req.attr.elementNo,
        PROPERTY_NAME=req.attr.propertyName,
        PROPERTY_VALUE=req.attr.propertyValue
    )
    return None


@http_service
def modify_element_property(req: RequestDTO):
    el_prop = TElementProperty.query_by(ELEMENT_NO=req.attr.elementNo, PROPERTY_NAME=req.attr.propertyName).first()
    Verify.not_empty(el_prop, '元素属性不存在')

    el_prop.property_value = req.attr.propertyValue
    el_prop.save()
    return None


@http_service
@db_transaction
def add_element_children(req: RequestDTO):
    add_element_child_with_transaction(
        parent_no=req.attr.parentNo,
        children=req.attr.children
    )
    return None


@http_service
@db_transaction
def modify_element_children(req: RequestDTO):
    modify_element_child_with_transaction(children=req.attr.children)


@http_service
def move_up_child_order(req: RequestDTO):
    child_rel = TElementChildRel.query_by(PARENT_NO=req.attr.parentNo, CHILD_NO=req.attr.childNo).first()
    Verify.not_empty(child_rel, '子元素不存在')

    children_length = TElementChildRel.query_by(PARENT_NO=req.attr.parentNo).count()
    child_current_order = child_rel.CHILD_ORDER
    if children_length == 1 or child_current_order == 1:
        return None

    upper_child_rel = TElementChildRel.query_by(
        PARENT_NO=req.attr.parentNo,
        CHILD_ORDER=child_current_order - 1
    ).first()
    upper_child_rel.update(CHILD_ORDER=upper_child_rel.CHILD_ORDER + 1)
    child_rel.update(CHILD_ORDER=child_rel.CHILD_ORDER - 1)

    return None


@http_service
def move_down_child_order(req: RequestDTO):
    child_rel = TElementChildRel.query_by(PARENT_NO=req.attr.parentNo, CHILD_NO=req.attr.childNo).first()
    Verify.not_empty(child_rel, '子元素不存在')

    children_length = TElementChildRel.query_by(PARENT_NO=req.attr.parentNo).count()
    current_child_order = child_rel.CHILD_ORDER
    if children_length == current_child_order:
        return None

    lower_child_rel = TElementChildRel.query_by(
        PARENT_NO=req.attr.parentNo,
        CHILD_ORDER=current_child_order + 1,
    ).first()
    lower_child_rel.update(CHILD_ORDER=lower_child_rel.CHILD_ORDER - 1)
    child_rel.update(CHILD_ORDER=child_rel.CHILD_ORDER + 1)

    return None


@http_service
def duplicate_element(req: RequestDTO):
    element = TTestElement.query_by(ELEMENT_NO=req.attr.element_no).first()
    Verify.not_empty(element, '测试元素不存在')

    # todo 复制元素
    return None


def create_element_with_transaction(element_name, element_comments, element_type,
                                    propertys: dict = None, children: [dict] = None):
    element_no = generate_no()
    TTestElement.create(
        commit=False,
        ELEMENT_NO=element_no,
        ELEMENT_NAME=element_name,
        ELEMENT_COMMENTS=element_comments,
        ELEMENT_TYPE=element_type,
        ENABLED=ElementStatus.ENABLE.value
    )
    db.session.flush()

    if propertys:
        add_element_property_with_transaction(element_no, propertys)
    if children:
        add_element_child_with_transaction(element_no, children)

    return element_no


def add_element_property_with_transaction(element_no, propertys: dict):
    for prop_name, prop_value in propertys.items():
        TElementProperty.create(
            commit=False,
            ELEMENT_NO=element_no,
            PROPERTY_NAME=prop_name,
            PROPERTY_VALUE=prop_value
        )

    db.session.flush()


def add_element_child_with_transaction(parent_no, children: [dict]):
    for child in children:
        child_no = create_element_with_transaction(
            element_name=child.get('elementName'),
            element_comments=child.get('elementComments'),
            element_type=child.get('elementType'),
            propertys=child.get('propertys'),
            children=child.get('children')
        )
        TElementChildRel.create(
            commit=False,
            PARENT_NO=parent_no,
            CHILD_NO=child_no,
            CHILD_ORDER=next_child_order(parent_no)
        )

    db.session.flush()


def modify_element_with_transaction(element_no, element_name, element_comments, element_type, propertys, children):
    element = TTestElement.query_by(ELEMENT_NO=element_no).first()
    Verify.not_empty(element, '测试元素不存在')

    if element_name is not None:
        element.ELEMENT_NAME = element_name
    if element_comments is not None:
        element.ELEMENT_COMMENTS = element_comments
    if element_type is not None:
        element.ELEMENT_TYPE = element_type

    element.save(commit=False)
    db.session.flush()

    if propertys is not None:
        modify_element_property_with_transaction(element_no, propertys)
    if children is not None:
        modify_element_child_with_transaction(children)


def modify_element_property_with_transaction(element_no, propertys: dict):
    for prop_name, prop_value in propertys.items():
        el_prop = TElementProperty.query_by(ELEMENT_NO=element_no, PROPERTY_NAME=prop_name).first()
        el_prop.PROPERTY_VALUE = prop_value
        el_prop.save(commit=False)

    db.session.flush()


def modify_element_child_with_transaction(children: [dict]):
    for child in children:
        if 'elementNo' not in child:
            raise ServiceError('子代元素编号不能为空')

        modify_element_with_transaction(
            element_no=child.get('elementNo'),
            element_name=child.get('elementName'),
            element_comments=child.get('elementComments'),
            element_type=child.get('elementType'),
            propertys=child.get('propertys'),
            children=child.get('children')
        )


def delete_element_with_transaction(element_no):
    element = TTestElement.query_by(ELEMENT_NO=element_no).first()
    Verify.not_empty(element, '测试元素不存在')

    result = [{
        'elementNo': element.ELEMENT_NO,
        'elementName': element.ELEMENT_NAME
    }]

    # 递归删除元素子代和关联关系
    result.extend(delete_child_with_transaction(element_no))
    # 如存在父辈关联关系，则删除关联并重新排序父辈子代
    child_rel = TElementChildRel.query_by(CHILD_NO=element_no).first()
    if child_rel:
        # 重新排序父辈子代
        TElementChildRel.query.filter(
            TElementChildRel.PARENT_NO == child_rel.PARENT_NO,
            TElementChildRel.CHILD_ORDER > child_rel.CHILD_ORDER
        ).update({TElementChildRel.CHILD_ORDER: TElementChildRel.CHILD_ORDER - 1})
        # 删除父辈关联
        child_rel.update(commit=False, DEL_STATE=1)

    # 删除元素属性
    delete_property_with_transaction(element_no)
    # 删除元素
    element.update(commit=False, DEL_STATE=1)

    db.session.flush()
    return result


def delete_child_with_transaction(element_no):
    child_rels = TElementChildRel.query_by(PARENT_NO=element_no).all()
    result = []
    for child_rel in child_rels:
        # 查询子代元素信息
        child = TTestElement.query_by(ELEMENT_NO=child_rel.child_no).first()
        if child:
            result.append({'elementNo': child.ELEMENT_NO, 'elementName': child.ELEMENT_NAME})

        result.extend(delete_child_with_transaction(child_rel.child_no))  # 递归删除子代元素的子代和关联关系
        # 删除父子关联关系
        child_rel.update(commit=False, DEL_STATE=1)
        # 删除子代元素属性
        delete_property_with_transaction(child_rel.child_no)
        # 删除子代元素
        child.update(commit=False, DEL_STATE=1)

    db.session.flush()
    return result


def delete_property_with_transaction(element_no):
    props = TElementProperty.query_by(ELEMENT_NO=element_no).all()
    for prop in props:
        prop.update(commit=False, DEL_STATE=1)

    db.session.flush()


def next_child_order(parent_no):
    return TElementChildRel.query_by(PARENT_NO=parent_no).count() + 1
