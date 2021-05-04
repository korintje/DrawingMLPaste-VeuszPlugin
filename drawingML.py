"""format for Microsoft Powerpoint images, shapes, and charts"""

# Import Python standard libralies
import io
import zipfile
import xml.etree.ElementTree as ET

# Import Veusz modules
# import veusz.qtall as qt
# import veusz.plugins as plugins

# Namespace prefixes of DrawingML
Override = r"{http://schemas.openxmlformats.org/package/2006/content-types}Override"
ChartType = r"application/vnd.openxmlformats-officedocument.drawingml.chart+xml"
c = r"{http://schemas.openxmlformats.org/drawingml/2006/chart}"
a = r"{http://schemas.openxmlformats.org/drawingml/2006/main}"

def getCharts(dmldata: bytearray) -> list:
    """Get DrawingML object from clipboard"""
    stream = io.BytesIO(dmldata)
    with zipfile.ZipFile(stream, "r") as z:
        with z.open("[Content_Types].xml") as f:
            tree = ET.fromstring(f.read())
        part_names = []
        for link in tree.findall(Override):
            content_type = link.attrib["ContentType"]
            if content_type == ChartType:
                part_name = link.attrib["PartName"]
                part_names.append(part_name)
        charts = []
        for part_name in part_names:
            with io.TextIOWrapper(z.open(part_name.strip("/"), "r"), encoding='utf-8') as f: 
                xmltext = f.read()
                chartfile = ChartFile(xmltext)
                charts.append(chartfile.chart)        
        return charts


class ChartFile():
    """chart.xml file in .zip container of DrawingML"""
    def __init__(self, xmltext):
        self.xmltext = xmltext
        self.parse()

    def parse(self):
        """get chart"""
        tree = ET.fromstring(self.xmltext)
        self.chart = Chart(tree.find(c + "chart"))


class Chart():
    """chart class"""
    def __init__(self, element):
        self.element = element
        self.title = "graph"
        self.axes = []
        self.scatterCharts = []
        self.barCharts = []
        self.parse()

    def parse(self):
        # Set chart title
        title_wrap = self.element.find(c + "title")
        if title_wrap:
            #title_words = title_wrap.find(c + "tx").find(c + "rich").find(a + "p").findall(a + "r")
            title_words = title_wrap.findall(".//" + a + "r")
            self.title = "".join([word.find(a + "t").text for word in title_words]) 
        # Set axes
        plotarea = self.element.find(c + "plotArea")
        valaxes = plotarea.findall(c + "valAx")
        cataxes = plotarea.findall(c + "catAx")
        for axis in valaxes:
            self.axes.append(Axis(axis, "num"))
        for axis in cataxes:
            self.axes.append(Axis(axis, "text"))
        # Set charts
        self.scatterCharts = [ScatterChart(element) for element in plotarea.findall(c + "scatterChart")]
        self.barCharts = [BarChart(element) for element in plotarea.findall(c + "barChart")]


class Axis():
    """Axis class"""
    def __init__(self, element, axistype):
        self.element = element
        self.type = axistype
        self.id = ""
        self.axPos = "" # "b": bottom, "l": left, "t": top, "r": right
        self.label = ""
        self.min = None
        self.max = None
        self.majorUnit = None
        self.minorUnit = None
        self.majorTickMark = None
        self.minorTickMark = None
        self.parse()

    def parse(self):
        self.id = self.element.find(c + "axId").get("val")
        self.axPos = self.element.find(c + "axPos").get("val")
        label_wrap = self.element.find(c + "title")
        if label_wrap:
            #label_words = label_wrap.find(c + "tx").find(c + "rich").find(a + "p").findall(a + "r")
            label_words = label_wrap.findall(".//" + a + "r")
            self.label = "".join([word.find(a + "t").text for word in label_words]) 
        scaling = self.element.find(c + "scaling")
        if scaling:
            axis_min = scaling.find(c + "min")
            if axis_min is not None:
                self.min = axis_min.get("val")
            axis_max = scaling.find(c + "max")
            if axis_max is not None:
                self.max = axis_max.get("val")
        majorUnit = self.element.find(c + "majorUnit")
        if majorUnit is not None:
            self.majorUnit = majorUnit.get("val")
        minorUnit = self.element.find(c + "minorUnit")
        if minorUnit is not None:
            self.minorUnit = minorUnit.get("val")


class ScatterChart():
    """Scatter chart"""
    def __init__(self, element):
        self.element = element
        self.xAxisID = ""
        self.yAxisID = ""
        self.parse()

    def parse(self):
        self.serieses = [xySeries(element) for element in self.element.findall(c + "ser")]
        axisIDs = self.element.findall(c + "axId")
        if len(axisIDs) == 2:
            self.xAxisID = axisIDs[0].get("val")
            self.yAxisID = axisIDs[1].get("val")


class BarChart():
    """Bar chart"""
    def __init__(self, element):
        self.element = element
        self.parse()

    def parse(self):
        self.serieses = [cvSeries(element) for element in self.element.findall(c + "ser")]


class xySeries():
    """Series made by x and y values"""
    def __init__(self, element):
        self.element = element
        self.xRef = ""
        self.yRef = ""
        self.x_vals = []
        self.y_vals = []
        self.parse()

    def parse(self):
        x_wrap = self.element.find(c + "xVal").find(c + "numRef")
        y_wrap = self.element.find(c + "yVal").find(c + "numRef")
        self.xRef = x_wrap.find(c + "f").text
        self.yRef = y_wrap.find(c + "f").text
        self.x_vals = [pt.find(c + "v").text for pt in x_wrap.find(c + "numCache").findall(c + "pt")]
        self.y_vals = [pt.find(c + "v").text for pt in y_wrap.find(c + "numCache").findall(c + "pt")]


class cvSeries():
    """Series made by category and y values"""
    def __init__(self, element):
        self.element = element
        self.catRef = ""
        self.valRef = ""
        self.cats = []
        self.vals = []
        self.parse()

    def parse(self):
        cat_wrap = self.element.find(c + "cat").find(c + "numRef")
        val_wrap = self.element.find(c + "val").find(c + "numRef")
        self.catRef = cat_wrap.find(c + "f").text
        self.valRef = val_wrap.find(c + "f").text
        self.cats = [v.find(c + "v").text for v in cat_wrap.find(c + "numCache").find(c + "pt")]
        self.vals = [v.find(c + "v").text for v in val_wrap.find(c + "numCache").find(c + "pt")]
