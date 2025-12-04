from docling.document_converter import DocumentConverter
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import *
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

from .intermediate_format.format_handler import HTMLFormatHandler

from .utils.docling_utils import export_to_html, vis_layout
from .extraction.extractor import JsonExtractor
from .utils.html_post_processor import enhance_html_for_extraction

class MERI:

    def __init__(self, pdf_path, chunks_max_characters=450000, model='gpt-4o-mini', model_temp=0.0,
                do_ocr = False, do_cell_matching: bool = True, enhance_layout: bool = True):
    
        self.pdf_path = pdf_path
        self.chunks_max_characters = chunks_max_characters
        self.model = model
        self.model_temp = model_temp
        self.enhance_layout = enhance_layout  # 是否启用布局增强（合并键值对）

        self.format_handler = None

        table_structure_options = TableStructureOptions(mode=TableFormerMode.ACCURATE,
                                                        do_cell_matching=do_cell_matching)

        pipeline_options = PdfPipelineOptions(generate_picture_images=True,
                                                generate_table_images=True,
                                                do_ocr=do_ocr,
                                                table_structure_options=table_structure_options)
        backend = PyPdfiumDocumentBackend
        self.converter = DocumentConverter(
            format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options = pipeline_options, backend = backend)
                    }
            )   

    def to_intermediate(self):
        self.docling_result = self.converter.convert(self.pdf_path)

        self.int_format = export_to_html(self.docling_result.document)
        
        # 如果启用布局增强，智能合并分离的键值对
        if self.enhance_layout:
            print("正在进行布局增强（合并分离的键值对）...")
            self.int_format = enhance_html_for_extraction(self.int_format)
            print("布局增强完成")
        
        self.format_handler = HTMLFormatHandler(self.int_format)

    def vis_layout(self, **kwargs):

        return vis_layout(self.docling_result, **kwargs)
    
    def run(self, json_schema_str: str):
        if not self.format_handler:
            self.to_intermediate()
        
        self.jsonExtractor = JsonExtractor(intermediate_format=self.format_handler,
                                            chunks_max_characters=self.chunks_max_characters, 
                                            model=self.model, 
                                            model_temp=self.model_temp)
                
        return self.jsonExtractor.populate_schema(json_schema_string=json_schema_str)
