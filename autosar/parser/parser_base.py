import abc
from collections import deque
from autosar.base import (AdminData, SpecialDataGroup, SpecialData, SwDataDefPropsConditional, SwPointerTargetProps, SymbolProps, SwCalprmAxis)
import autosar.element

def _parseBoolean(value):
    if value is None:
        return None
    if isinstance(value,str):
        if value == 'true': return True
        elif value =='false': return False
    raise ValueError(value)

class CommonTagsResult:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.adminData = None
        self.desc = None
        self.descAttr = None
        self.longName = None
        self.longNameAttr = None
        self.name = None
        self.category = None


class BaseParser:
    def __init__(self,version=None):
        self.version = version
        self.common = deque()
    
    def push(self):
        self.common.append(CommonTagsResult())
    
    def pop(self, obj = None):
        if obj is not None:
            self.applyDesc(obj)
            self.applyLongName(obj)
        self.common.pop()

    
        

    def baseHandler(self, xmlElem):
        """
        Alias for defaultHandler
        """
        self.defaultHandler(xmlElem)
        
    def defaultHandler(self, xmlElem):
        """
        A default handler that parses common tags found under most XML elements
        """
        if xmlElem.tag == 'SHORT-NAME':
            self.common[-1].name = self.parseTextNode(xmlElem)
        elif xmlElem.tag == 'ADMIN-DATA':
            self.common[-1].adminData = self.parseAdminDataNode(xmlElem)
        elif xmlElem.tag == 'CATEGORY':
            self.common[-1].category = self.parseTextNode(xmlElem)
        elif xmlElem.tag == 'DESC':
            self.common[-1].desc, self.common[-1].desc_attr = self.parseDescDirect(xmlElem)
        elif xmlElem.tag == 'LONG-NAME':
            self.common[-1].longName, self.common[-1].longName_attr = self.parseLongNameDirect(xmlElem)
        else:
            raise NotImplementedError(xmlElem.tag)
    
    def applyDesc(self, obj):
        if self.common[-1].desc is not None:            
            obj.desc=self.common[-1].desc
            obj.descAttr=self.common[-1].desc_attr

    def applyLongName(self, obj):
        if self.common[-1].longName is not None:            
            obj.longName=self.common[-1].longName
            obj.longNameAttr=self.common[-1].longName_attr
    
    @property
    def name(self):
        return self.common[-1].name

    @property
    def adminData(self):
        return self.common[-1].adminData

    @property
    def category(self):
        return self.common[-1].category

    @property
    def desc(self):
        return self.common[-1].desc, self.common[-1].descAttr

    def parseLongName(self, xmlRoot, elem):
        xmlDesc = xmlRoot.find('LONG-NAME')
        if xmlDesc is not None:
            L2Xml = xmlDesc.find('L-4')
            if L2Xml is not None:
                L2Text=self.parseTextNode(L2Xml)
                L2Attr=L2Xml.attrib['L']
                elem.desc=L2Text
                elem.descAttr=L2Attr

    def parseLongNameDirect(self, xmlLongName):
        assert(xmlLongName.tag == 'LONG-NAME')
        L2Xml = xmlLongName.find('L-4')
        if L2Xml is not None:
            L2Text=self.parseTextNode(L2Xml)
            L2Attr=L2Xml.attrib['L']
            return (L2Text, L2Attr)
        return (None, None)

    def parseDesc(self, xmlRoot, elem):
        xmlDesc = xmlRoot.find('DESC')
        if xmlDesc is not None:
            L2Xml = xmlDesc.find('L-2')
            if L2Xml is not None:
                L2Text=self.parseTextNode(L2Xml)
                L2Attr=L2Xml.attrib['L']
                elem.desc=L2Text
                elem.descAttr=L2Attr

    def parseDescDirect(self, xmlDesc):
        assert(xmlDesc.tag == 'DESC')
        L2Xml = xmlDesc.find('L-2')
        if L2Xml is not None:
            L2Text=self.parseTextNode(L2Xml)
            L2Attr=L2Xml.attrib['L']
            return (L2Text, L2Attr)
        return (None, None)

    def parseTextNode(self, xmlElem):
        return None if xmlElem is None else xmlElem.text

    def parseIntNode(self, xmlElem):
        return None if xmlElem is None else int(xmlElem.text)

    def parseFloatNode(self, xmlElem):
        return None if xmlElem is None else float(xmlElem.text)

    def parseBooleanNode(self, xmlElem):
        return None if xmlElem is None else _parseBoolean(xmlElem.text)

    def parseNumberNode(self, xmlElem):
        textValue = self.parseTextNode(xmlElem)
        retval = None
        if textValue is not None:
            try:
                retval = int(textValue)
            except ValueError:
                try:
                    retval = float(textValue)
                except ValueError:
                    retval = textValue
        return retval

    def hasAdminData(self, xmlRoot):
        return True if xmlRoot.find('ADMIN-DATA') is not None else False

    def parseAdminDataNode(self, xmlRoot):
        if xmlRoot is None: return None
        assert(xmlRoot.tag=='ADMIN-DATA')
        adminData=AdminData()
        xmlSDGS = xmlRoot.find('./SDGS')
        if xmlSDGS is not None:
            for xmlElem in xmlSDGS.findall('./SDG'):
                SDG_GID=xmlElem.attrib['GID']
                specialDataGroup = SpecialDataGroup(SDG_GID)
                for xmlChild in xmlElem.findall('./*'):
                    if xmlChild.tag == 'SD':
                        SD_GID = None
                        TEXT=xmlChild.text
                        try:
                            SD_GID=xmlChild.attrib['GID']
                        except KeyError: pass
                        specialDataGroup.SD.append(SpecialData(TEXT, SD_GID))
                    else:
                        raise NotImplementedError(xmlChild.tag)
                adminData.specialDataGroups.append(specialDataGroup)
        return adminData

    def parseSwDataDefProps(self, xmlRoot):
        assert (xmlRoot.tag == 'SW-DATA-DEF-PROPS')
        variants = []
        for itemXML in xmlRoot.findall('./*'):
            if itemXML.tag == 'SW-DATA-DEF-PROPS-VARIANTS':
                for subItemXML in itemXML.findall('./*'):
                    if subItemXML.tag == 'SW-DATA-DEF-PROPS-CONDITIONAL':
                        variant = self.parseSwDataDefPropsConditional(subItemXML)
                        assert(variant is not None)
                        variants.append(variant)
                    else:
                        raise NotImplementedError(subItemXML.tag)
            else:
                raise NotImplementedError(itemXML.tag)
        return variants if len(variants)>0 else None

    def parseSwDataDefPropsConditional(self, xmlRoot):
        assert (xmlRoot.tag == 'SW-DATA-DEF-PROPS-CONDITIONAL')
        (baseTypeRef, implementationTypeRef, swCalibrationAccess, compuMethodRef, dataConstraintRef,
            swPointerTargetPropsXML, swImplPolicy, swAddressMethodRef, unitRef, calPrmAxisSetXML, swRecordLayoutRef,
            additionalNativeTypeQualifier, invalidValueXML) = (None, None, None, None, None, None, None, None, None, None, None, None, None)
        for xmlItem in xmlRoot.findall('./*'):
            if xmlItem.tag == 'BASE-TYPE-REF':
                baseTypeRef = self.parseTextNode(xmlItem)
            elif xmlItem.tag == 'SW-CALIBRATION-ACCESS':
                swCalibrationAccess = self.parseTextNode(xmlItem)
            elif xmlItem.tag == 'COMPU-METHOD-REF':
                compuMethodRef = self.parseTextNode(xmlItem)
            elif xmlItem.tag == 'DATA-CONSTR-REF':
                dataConstraintRef = self.parseTextNode(xmlItem)
            elif xmlItem.tag == 'SW-POINTER-TARGET-PROPS':
                swPointerTargetPropsXML = xmlItem
            elif xmlItem.tag == 'IMPLEMENTATION-DATA-TYPE-REF':
                implementationTypeRef = self.parseTextNode(xmlItem)
            elif xmlItem.tag == 'SW-IMPL-POLICY':
                swImplPolicy = self.parseTextNode(xmlItem)
            elif xmlItem.tag == 'SW-ADDR-METHOD-REF':
                swAddressMethodRef = self.parseTextNode(xmlItem)
            elif xmlItem.tag == 'UNIT-REF':
                unitRef = self.parseTextNode(xmlItem)
            elif xmlItem.tag == 'ADDITIONAL-NATIVE-TYPE-QUALIFIER':
                additionalNativeTypeQualifier = self.parseTextNode(xmlItem)
            elif xmlItem.tag == 'SW-CALPRM-AXIS-SET':
                calPrmAxisSetXML = xmlItem
            elif xmlItem.tag == 'SW-RECORD-LAYOUT-REF':
                swRecordLayoutRef = self.parseTextNode(xmlItem)
            elif xmlItem.tag == 'INVALID-VALUE':
                invalidValueXML = xmlItem
            else:
                raise NotImplementedError(xmlItem.tag)
        variant = SwDataDefPropsConditional(baseTypeRef, implementationTypeRef, swAddressMethodRef, swCalibrationAccess,
                    swImplPolicy, None, compuMethodRef, dataConstraintRef, unitRef, swRecordLayoutRef, additionalNativeTypeQualifier)
        if swPointerTargetPropsXML is not None:
            variant.swPointerTargetProps = self.parseSwPointerTargetProps(swPointerTargetPropsXML, variant)

        if calPrmAxisSetXML is not None:
            calPrmAxisSet = []
            for xmlChild in calPrmAxisSetXML.findall('./*'):
                if xmlChild.tag == 'SW-CALPRM-AXIS':
                    calPrmAxisSet.append(self.parseSwCalprmAxis(xmlChild, variant))
            variant.calPrmAxisSet = calPrmAxisSet

        if invalidValueXML is not None:
            values = self.parseValueV4(invalidValueXML, variant)
            if len(values) != 1:
                raise ValueError('A value specification must contain exactly one element')
            variant.invalidValue = values[0]

        return variant

    def parseSwCalprmAxis(self, rootXML, parent = None):
        assert (rootXML.tag == 'SW-CALPRM-AXIS')
        (swAxisIndex, calibrationAccess, category, displayFormat, baseTypeRef, swAxisGroupedSharedAxisRef,
            swAxisGroupedIndex, swAxisIndividualXML) = (None, None, None, None, None, None, None, None)
        for itemXML in rootXML.findall('./*'):
            if itemXML.tag == 'SW-AXIS-INDEX':
                swAxisIndex = self.parseNumberNode(itemXML)
            elif itemXML.tag == 'CATEGORY':
                category = self.parseTextNode(itemXML)
            elif itemXML.tag == 'SW-AXIS-GROUPED':
                for childXML in itemXML.findall('./*'):
                    if childXML.tag == 'SHARED-AXIS-TYPE-REF':
                        swAxisGroupedSharedAxisRef = self.parseTextNode(childXML)
                    elif childXML.tag == 'SW-AXIS-INDEX':
                        swAxisGroupedIndex = self.parseNumberNode(childXML)
                    else:
                        raise NotImplementedError(childXML.tag)
            elif itemXML.tag == 'SW-AXIS-INDIVIDUAL':
                swAxisIndividualXML = itemXML
            elif itemXML.tag == 'SW-CALIBRATION-ACCESS':
                calibrationAccess = self.parseTextNode(itemXML)
            elif itemXML.tag == 'DISPLAY-FORMAT':
                calibrationAccess = self.parseTextNode(itemXML)
            elif itemXML.tag == 'BASE-TYPE-REF':
                baseTypeRef = self.parseTextNode(itemXML)
            else:
                raise NotImplementedError(itemXML.tag)
        axis = SwCalprmAxis(swAxisIndex = swAxisIndex, calibrationAccess = calibrationAccess,
                category = category, displayFormat = displayFormat, baseTypeRef = baseTypeRef,
                swAxisGroupedSharedAxisRef = swAxisGroupedSharedAxisRef, swAxisGroupedIndex = swAxisGroupedIndex, parent = parent)

        if swAxisIndividualXML is not None:
            swAxisIndividual = autosar.base.SwCalprmAxisIndividual(parent=axis)
            axis.swAxisIndividual = swAxisIndividual
            for childXML in swAxisIndividualXML.findall('./*'):
                if childXML.tag == 'COMPU-METHOD-REF':
                    swAxisIndividual.compuMethodRef = self.parseTextNode(childXML)
                elif childXML.tag == 'UNIT-REF':
                    swAxisIndividual.unitRef = self.parseTextNode(childXML)
                elif childXML.tag == 'SW-MAX-AXIS-POINTS':
                    swAxisIndividual.swMaxAxisPoints = self.parseNumberNode(childXML)
                elif childXML.tag == 'SW-MIN-AXIS-POINTS':
                    swAxisIndividual.swMinAxisPoints = self.parseNumberNode(childXML)
                elif childXML.tag == 'DATA-CONSTR-REF':
                    swAxisIndividual.dataConstraintRef = self.parseTextNode(childXML)
                else:
                    raise NotImplementedError(childXML.tag)

        return axis

    def parseSwPointerTargetProps(self, rootXML, parent = None):
        assert (rootXML.tag == 'SW-POINTER-TARGET-PROPS')
        props = SwPointerTargetProps()
        for itemXML in rootXML.findall('./*'):
            if itemXML.tag == 'TARGET-CATEGORY':
                props.targetCategory = self.parseTextNode(itemXML)
            if itemXML.tag == 'SW-DATA-DEF-PROPS':
                props.variants = self.parseSwDataDefProps(itemXML)
        return props

    def parseVariableDataPrototype(self, xmlRoot, parent = None):
        assert(xmlRoot.tag == 'VARIABLE-DATA-PROTOTYPE')
        (typeRef, props_variants, isQueued) = (None, None, False)
        self.push()
        for xmlElem in xmlRoot.findall('./*'):
            if xmlElem.tag == 'TYPE-TREF':
                typeRef = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'SW-DATA-DEF-PROPS':
                props_variants = self.parseSwDataDefProps(xmlElem)
            else:
                self.defaultHandler(xmlElem)
        if (self.name is not None) and (typeRef is not None):
            dataElement = autosar.element.DataElement(self.name, typeRef, isQueued, category=self.category, parent = parent, adminData = self.adminData)
            if (props_variants is not None) and len(props_variants) > 0:
                dataElement.setProps(props_variants[0])
            self.pop(dataElement)
            return dataElement
        else:
            self.pop()
            raise RuntimeError('SHORT-NAME and TYPE-TREF must not be None')
        
    
    def parseSymbolProps(self, xmlRoot):
        assert(xmlRoot.tag == 'SYMBOL-PROPS')
        name, symbol = None, None
        for xmlElem in xmlRoot.findall('./*'):
            if xmlElem.tag == 'SHORT-NAME':
                name = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'SYMBOL':
                symbol = self.parseTextNode(xmlElem)
            else:
                raise NotImplementedError(xmlElem.tag)
        return SymbolProps(name, symbol)

    def parseValueV4(self, xmlValue, parent):
        result = []
        for xmlElem in xmlValue.findall('./*'):
            if xmlElem.tag == 'TEXT-VALUE-SPECIFICATION':
                result.append(self._parseTextValueSpecification(xmlElem, parent))
            elif xmlElem.tag == 'RECORD-VALUE-SPECIFICATION':
                result.append(self._parseRecordValueSpecification(xmlElem, parent))
            elif xmlElem.tag == 'NUMERICAL-VALUE-SPECIFICATION':
                result.append(self._parseNumericalValueSpecification(xmlElem, parent))
            elif xmlElem.tag == 'ARRAY-VALUE-SPECIFICATION':
                result.append(self._parseArrayValueSpecification(xmlElem, parent))
            elif xmlElem.tag == 'CONSTANT-REFERENCE':
                result.append(self._parseConstantReference(xmlElem, parent))
            elif xmlElem.tag == 'APPLICATION-VALUE-SPECIFICATION':
                result.append(self._parseApplicationValueSpecification(xmlElem, parent))
            else:
                raise NotImplementedError(xmlElem.tag)
        return result

    def _parseTextValueSpecification(self, xmlValue, parent):
        (label, value) = (None, None)
        for xmlElem in xmlValue.findall('./*'):
            if xmlElem.tag == 'SHORT-LABEL':
                label = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'VALUE':
                value = self.parseTextNode(xmlElem)
            else:
                raise NotImplementedError(xmlElem.tag)

        if value is not None:
            return autosar.constant.TextValue(label, value, parent)
        else:
            raise RuntimeError("Value must not be None")

    def _parseNumericalValueSpecification(self, xmlValue, parent):
        (label, value) = (None, None)
        for xmlElem in xmlValue.findall('./*'):
            if xmlElem.tag == 'SHORT-LABEL':
                label = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'VALUE':
                value = self.parseTextNode(xmlElem)
            else:
                raise NotImplementedError(xmlElem.tag)

        if value is not None:
            return autosar.constant.NumericalValue(label, value, parent)
        else:
            raise RuntimeError("value must not be None")

    def _parseRecordValueSpecification(self, xmlValue, parent):
        (label, xmlFields) = (None, None)
        for xmlElem in xmlValue.findall('./*'):
            if xmlElem.tag == 'SHORT-LABEL':
                label = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'FIELDS':
                xmlFields = xmlElem
            else:
                raise NotImplementedError(xmlElem.tag)

        if (xmlFields is not None):
            record = autosar.constant.RecordValue(label, parent=parent)
            record.elements = self.parseValueV4(xmlFields, record)
            return record
        else:
            raise RuntimeError("<FIELDS> must not be None")

    def _parseArrayValueSpecification(self, xmlValue, parent):
        (label, xmlElements) = (None, None)
        for xmlElem in xmlValue.findall('./*'):
            if xmlElem.tag == 'SHORT-LABEL':
                label = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'ELEMENTS':
                xmlElements = xmlElem
            else:
                raise NotImplementedError(xmlElem.tag)

        if (xmlElements is not None):
            array = autosar.constant.ArrayValueAR4(label, parent=parent)
            array.elements = self.parseValueV4(xmlElements, array)
            return array

        else:
            raise RuntimeError("<ELEMENTS> must not be None")

    def _parseConstantReference(self, xmlRoot, parent):
        label, constantRef = None, None
        self.push()
        for xmlElem in xmlRoot.findall('./*'):
            if xmlElem.tag == 'SHORT-LABEL':
                label = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'CONSTANT-REF':
                constantRef = self.parseTextNode(xmlElem)
            else:
                self.baseHandler(xmlElem)
        if constantRef is not None:
            obj = autosar.constant.ConstantReference(label, constantRef, parent, self.adminData)
            self.pop(obj)
            return obj
        else:
            raise RuntimeError('<CONSTANT-REF> must not be None')

    def _parseApplicationValueSpecification(self, xmlRoot, parent):
        label, swValueCont, swAxisCont, category = None, None, None, None

        for xmlElem in xmlRoot.findall('./*'):
            if xmlElem.tag == 'SHORT-LABEL':
                label = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'CATEGORY':
                category = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'SW-VALUE-CONT':
                swValueCont = self._parseSwValueCont(xmlElem)
            elif xmlElem.tag == 'SW-AXIS-CONTS':
                xmlChild = xmlElem.find('./SW-AXIS-CONT')
                if xmlChild is not None:
                    swAxisCont = self._parseSwAxisCont(xmlChild)
            else:
                raise NotImplementedError(xmlElem.tag)
        value = autosar.constant.ApplicationValue(label, swValueCont = swValueCont, swAxisCont = swAxisCont, category = category, parent = parent)
        return value

    def _parseSwValueCont(self, xmlRoot):
        unitRef = None
        valueList = []
        for xmlElem in xmlRoot.findall('./*'):
            if xmlElem.tag == 'UNIT-REF':
                unitRef = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'SW-VALUES-PHYS':
                for xmlChild in xmlElem.findall('./*'):
                    if (xmlChild.tag == 'V') or (xmlChild.tag == 'VF'):
                        valueList.append(self.parseNumberNode(xmlChild))
                    elif xmlChild.tag == 'VT':
                        valueList.append(self.parseTextNode(xmlChild))
                    else:
                        raise NotImplementedError(xmlChild.tag)
            else:
                raise NotImplementedError(xmlElem.tag)
        if len(valueList)==0:
            valueList = None
        return autosar.constant.SwValueCont(valueList, unitRef)

    def _parseSwAxisCont(self, xmlRoot):
        unitRef = None
        valueList = []
        for xmlElem in xmlRoot.findall('./*'):
            if xmlElem.tag == 'UNIT-REF':
                unitRef = self.parseTextNode(xmlElem)
            elif xmlElem.tag == 'SW-VALUES-PHYS':
                for xmlChild in xmlElem.findall('./*'):
                    if xmlChild.tag == 'V':
                        valueList.append(self.parseNumberNode(xmlChild))
                    else:
                        raise NotImplementedError(xmlChild.tag)
            else:
                raise NotImplementedError(xmlElem.tag)
        if len(valueList)==0:
            valueList = None
        return autosar.constant.SwAxisCont(valueList, unitRef)

class ElementParser(BaseParser, metaclass=abc.ABCMeta):

    def __init__(self, version=None):
        super().__init__(version)

    @abc.abstractmethod
    def getSupportedTags(self):
        """
        Returns a list of tag-names (strings) that this parser supports.
        A generator returning strings is also OK.
        """
    @abc.abstractmethod
    def parseElement(self, xmlElement, parent = None):
        """
        Invokes the parser

        xmlElem: Element to parse (instance of xml.etree.ElementTree.Element)
        parent: the parent object (usually a package object)
        Should return an object derived from autosar.element.Element
        """
