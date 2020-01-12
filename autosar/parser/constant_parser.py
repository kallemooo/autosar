from autosar.element import Element
import autosar.constant
from autosar.base import hasAdminData,parseAdminDataNode
from autosar.parser.parser_base import ElementParser

class ConstantParser(ElementParser):
    """
    Constant package parser
    """
    def __init__(self,version=3.0):
        super().__init__(version)

    def getSupportedTags(self):
        return ['CONSTANT-SPECIFICATION']

    def parseElement(self, xmlElement, parent = None):
        if xmlElement.tag == 'CONSTANT-SPECIFICATION':
            return self.parseConstantSpecification(xmlElement, parent)
        else:
            return None

    def parseConstantSpecification(self, xmlElem, rootProject=None, parent=None):
        assert(xmlElem.tag == 'CONSTANT-SPECIFICATION')
        (xmlValue, xmlValueSpec) = (None, None)
        self.push()
        for xmlElem in xmlElem.findall('./*'):
            if self.version < 4.0 and xmlElem.tag == 'VALUE':
                xmlValue = xmlElem
            elif self.version >= 4.0 and xmlElem.tag == 'VALUE-SPEC':
                xmlValueSpec = xmlElem
            elif xmlElem.tag == 'TYPE-TREF':
                typeRef = self.parseTextNode(xmlElem)
            else:
                self.defaultHandler(xmlElem)

        if (self.name is not None) and ((xmlValue is not None) or (xmlValueSpec is not None)):
            constant = autosar.constant.Constant(self.name, parent=parent, adminData=self.adminData)
            if xmlValue is not None:
                constant.value = self._parseValueV3(xmlValue.find('./*') , constant)
            elif xmlValueSpec is not None:
                values = self.parseValueV4(xmlValueSpec, constant)
                if len(values) != 1:
                    raise ValueError('A value specification must contain exactly one element')
                constant.value = values[0]
            retval = constant
        else:
            retval = None
        self.pop(retval)
        return retval

    def _parseValueV3(self, xmlValue, parent):
        constantValue = None
        xmlName = xmlValue.find('SHORT-NAME')
        if xmlName is not None:
            name=xmlName.text
            if xmlValue.tag == 'INTEGER-LITERAL':
                typeRef = xmlValue.find('./TYPE-TREF').text
                innerValue = xmlValue.find('./VALUE').text
                constantValue = autosar.constant.IntegerValue(name, typeRef, innerValue, parent)
            elif xmlValue.tag=='STRING-LITERAL':
                typeRef = xmlValue.find('./TYPE-TREF').text
                innerValue = xmlValue.find('./VALUE').text
                constantValue = autosar.constant.StringValue(name, typeRef, innerValue, parent)
            elif xmlValue.tag=='BOOLEAN-LITERAL':
                typeRef = xmlValue.find('./TYPE-TREF').text
                innerValue = xmlValue.find('./VALUE').text
                constantValue = autosar.constant.BooleanValue(name, typeRef, innerValue, parent)
            elif xmlValue.tag == 'RECORD-SPECIFICATION' or xmlValue.tag == 'ARRAY-SPECIFICATION':
                typeRef = xmlValue.find('./TYPE-TREF').text
                if xmlValue.tag == 'RECORD-SPECIFICATION':
                    constantValue=autosar.constant.RecordValue(name, typeRef, parent=parent)
                else:
                    constantValue=autosar.constant.ArrayValue(name, typeRef, parent=parent)
                for innerElem in xmlValue.findall('./ELEMENTS/*'):
                    innerConstant = self._parseValueV3(innerElem, constantValue)
                    if innerConstant is not None:
                        constantValue.elements.append(innerConstant)
        return constantValue
