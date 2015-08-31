# coding=utf-8
__author__ = 'hz'
import xlrd
import xlwt
import os
import time
import nltk
from nltk.parse import stanford
from practnlptools.tools import Annotator

class ExcelReader():
    "an excel file with only one sheet by default"
    def __init__( self, xlsfile ):
        self.file_name = xlsfile
        self.book = xlrd.open_workbook( xlsfile )
        self.sheet_name = self.book.sheet_names()[0]
        self.sheet = self.book.sheet_by_index( 0 )

    def getCellData( self, row_num, col_num ):
        return self.sheet.cell_value( row_num, col_num )

    def getRowData( self, row_num ):
        return self.sheet.row_values( row_num )

    def getColData( self, col_num ):
        return self.sheet.col_values( col_num )

    def getNumRows( self ):
        return self.sheet.nrows

    def getNumCols( self ):
        return self.sheet.ncols

class SAOData(object):
    def __init__( self ):
        self.index = -1
        self.subject = ''
        self.datas = {'V':'',
                      'A0':'',
                      'A1':'',
                      'A2':'',
                      'AM-ADV':'',
                      'AM-DIR':'',
                      'AM-DIS':'',
                      'AM-EXT':'',
                      'AM-LOC':'',
                      'AM-MNR':'',
                      'AM-MOD':'',
                      'AM-NEG':'',
                      'AM-PNC':'',
                      'AM-PRD':'',
                      'AM-PRP':'',
                      'AM-REC':'',
                      'AM-TMP':''
                      }

class SAOParserCore():
    def __init__( self ):
        pass

    def sentsTokenize( self, text ):
        """
        :param text: text to split into sentences
        :return:
        :rtype: list(str)
        """
        return nltk.sent_tokenize( text )

    def wordsTokenize( self, sentence ):
        return nltk.word_tokenize( sentence )

    def sentsParser( self, sentences ):
        """
        Use StanfordParser to parse multiple sentences. Takes multiple sentences as a
        list of strings.
        Each sentence will be automatically tokenized and tagged by the Stanford Parser.

        :param sentences:
        :type sentences: list(str)
        :return:
        :rtype: iter(iter(Tree))
        """
        stanford_parser = stanford.StanfordParser( model_path= "englishPCFG.ser.gz")
        return stanford_parser.raw_parse_sents( self.sentsTokenize( sentences ) )

    def getParserTree( self, sentence ):
        sentences_trees = self.sentsParser( sentence )
        paser_tree = None
        for line in sentences_trees:
            for item in line:
                paser_tree = item
        return paser_tree

    def SRLAnnotation( self, sentence ):
        """
        Use SENNA library to perform SRL(semantic role labelling) on specific sentence.

        :param sentence: the specific sentence to be handled
        :type sentence: str
        :return:
        :rtype: list({})
        """
        annotator = Annotator()
        return annotator.getAnnotations( sentence )["srl"]


class SAOSystem(object):
    thesaurus = frozenset()
    def __init__(self, sublist_file_name = r'sublist.txt' ):
        self.__class__.thesaurus = frozenset( self.init_sublist( sublist_file_name) )

    # def __index( self, alist, element ):
    #     """
    #     find the specific element index in a list
    #     :param alist: list
    #     :param element:
    #     :return: list of the index
    #     """
    #     if isinstance( alist, list ):
    #         result = []
    #         for index, item in enumerate( alist ):
    #             if item == element:
    #                 result.append( index )
    #         return result
    #     else:
    #         raise TypeError("parameter must be list type, not %s" %
    #                         (type( alist ).__name__))

    def __isVerb( self, paser_tree, word ):
        """
        :param paser_tree:
        :param word:
        :return: boolean type
        """
        leaves = paser_tree.leaves()
        index = leaves.index( word )
        atuple = paser_tree.leaf_treeposition( index )
        atuple = atuple[ 0:-1 ]
        #get the node content
        node_label = paser_tree[ atuple ].label()
        if 'JJ' == node_label or 'NNP' == node_label:
            return False
        else:
            return True

    def __compositeSubject( self, alist ):
        result = ''
        for item in alist:
            result = result + ' ' + item
        return result.strip()

    def findSubject( self, paser_tree, word ):
        leaves = paser_tree.leaves()
        index = leaves.index( word )
        atuple = paser_tree.leaf_treeposition( index )

        atuple = atuple[ 0:-1 ]
        while atuple:
            parent_tree = paser_tree[ atuple ]
            if 'S' == parent_tree.label():
                if self.__findSubject( parent_tree ):
                    return self.__findSubject( parent_tree )

            atuple = atuple[ 0:-1]
        return None

    def __findSubject( self, paser_tree ):
        for i in range( len( paser_tree ) ):
            if 'NP' == paser_tree[i].label():
                result = paser_tree[i].leaves()
                result = self.__compositeSubject( result )
                return result
            elif 'S' == paser_tree[i].label():
                return self.__findSubject( paser_tree[i] )

        return None



    def run( self, input_file_name = r'data.xls', result_file_name = r'result.xls' ):

        sao_parser = SAOParserCore()
        excel_reader = ExcelReader( input_file_name )

        #[[index, text],[]]
        all_text = []
        num_rows = excel_reader.getNumRows()
        for row_num in range( 1, num_rows ):
            result = []
            result.append( excel_reader.getCellData( row_num, 0 ) )
            result.append( excel_reader.getCellData( row_num, 1 ) )
            all_text.append( result )


        #[[index, sentence1, sentence2,...],[...],[...]]
        sentences_process = []
        for text in all_text:
            sentences = sao_parser.sentsTokenize( text[1] )
            results = []
            results.append( text[0] )
            for sentence in sentences:
                words = sao_parser.wordsTokenize( sentence )
                for word in words:
                    if word in self.__class__.thesaurus:
                        results.append( sentence )
                        break
            sentences_process.append( results )

        #[ SAOData1, SAOData2 ]
        output_datas = []

        for index, sentences in enumerate( sentences_process ):
            print(u"共有%d条数据，正在处理第%d条数据，已完成%.2f%%" %( num_rows - 1, index + 1, float(index)/(num_rows-1) * 100 ) )
            for sentence in sentences[1:]:
                srl_result = sao_parser.SRLAnnotation( sentence )
                paser_tree = sao_parser.getParserTree( sentence )
                for item in srl_result:
                    if self.__isVerb( paser_tree, item['V'] ):
                        element = SAOData()
                        element.index = sentences[0]
                        element.subject = self.findSubject( paser_tree, item['V'] )
                        for key in item.keys():
                            element.datas[key] = item[key]

                        output_datas.append( element )
        self.excel_writer( output_datas )
        print(u"-----任务完成啦T_T-----")

    def init_sublist( self, file_name = r'sublist.txt'):
        thesaurus = set()
        f = open( file_name, 'r' )
        while True:
            line = f.readline()
            if line:
                line = line.strip()
                thesaurus.add( line )
            else:
                break
        return thesaurus


    def excel_writer( self, datas, file_name = "result.xls", path = '.\\' ):
        font = xlwt.Font()
        font.colour_index = 2
        font.bold= True

        style = xlwt.XFStyle()
        style.font = font
        # check the parameter

        # build the unique file name
        now_time = time.strftime( '%Y-%m-%d %H-%M-%S', time.localtime() )
        xls_full_path = path + now_time + ' ' + file_name

        book = xlwt.Workbook( encoding = 'utf-8', style_compression = 0 )
        sheet = book.add_sheet( 'result', cell_overwrite_ok = True )
        sheet.write( 0, 0, 'index' )

        sheet_names = ['index', 'S', 'A0', 'V', 'A1', 'A2', 'AM-ADV', 'AM-DIR', 'AM-DIS', 'AM-EXT',
                      'AM-LOC', 'AM-MNR', 'AM-MOD', 'AM-NEG', 'AM-PNC', 'AM-PRD', 'AM-PRP', 'AM-REC', 'AM-TMP']
        for i, name in enumerate( sheet_names ):
            if 'S' == name:
                sheet.write( 0, i, name, style )
            else:
                sheet.write( 0, i, name )

        row_num = 1
        for data in datas:
            sheet.write( row_num, 0, data.index )
            sheet.write( row_num, 1, data.subject, style )
            for col_num in range( 2, len(sheet_names) ):
                sheet.write( row_num, col_num, data.datas[sheet_names[col_num]])
            row_num += 1

        book.save( xls_full_path )


if __name__ == '__main__':
    sao_system = SAOSystem('sublist.txt')
    print(u'开始处理，请稍后...')
    sao_system.run('data.xls')