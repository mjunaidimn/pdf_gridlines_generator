"""
PDF Gridline Generator
Creates gridlines on PDF pages to help identify field coordinates
"""

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import List, Tuple
import zipfile

# Try imports
try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    st.error("PyMuPDF not installed. Run: pip install PyMuPDF")

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    st.error("ReportLab not installed. Run: pip install reportlab")


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Application configuration"""
    
    PAGE_CONFIG = {
        "page_title": "PDF Gridline Generator",
        "page_icon": "📐",
        "layout": "wide"
    }
    
    PDF_DPI = 200
    
    # Default gridline settings
    DEFAULT_H_SPACING = 50
    DEFAULT_V_SPACING = 50
    DEFAULT_GRID_COLOR = (200, 200, 200)  # Light gray
    DEFAULT_LABEL_COLOR = (100, 100, 100)  # Dark gray
    DEFAULT_LINE_WIDTH = 1
    
    # Grid label settings
    LABEL_FONT_SIZE = 8
    LABEL_OFFSET = 2


# ============================================================================
# PDF PROCESSOR
# ============================================================================

class PDFProcessor:
    """PDF processing utilities"""
    
    def __init__(self, dpi: int = Config.PDF_DPI):
        self.dpi = dpi
        self.zoom = dpi / 72
    
    def pdf_to_images(self, pdf_bytes: bytes) -> List[Image.Image]:
        """Convert PDF to images"""
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF required")
        
        try:
            images = []
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            mat = fitz.Matrix(self.zoom, self.zoom)
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")
                img = Image.frombytes("RGB", [pix.width, pix.height], img_data)
                images.append(img)
            
            pdf_document.close()
            return images
        except Exception as e:
            raise ValueError(f"Failed to convert PDF: {str(e)}")
    
    def get_pdf_info(self, pdf_bytes: bytes) -> dict:
        """Get PDF information"""
        if not PYMUPDF_AVAILABLE:
            return {}
        
        try:
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            info = {
                "page_count": pdf_document.page_count,
                "pages": []
            }
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                rect = page.rect
                info["pages"].append({
                    "page_number": page_num,
                    "width": rect.width,
                    "height": rect.height
                })
            
            pdf_document.close()
            return info
        except:
            return {}


# ============================================================================
# GRIDLINE GENERATOR
# ============================================================================

class GridlineGenerator:
    """Generate gridlines on images"""
    
    def __init__(self, 
                 h_spacing: int = Config.DEFAULT_H_SPACING,
                 v_spacing: int = Config.DEFAULT_V_SPACING,
                 grid_color: Tuple[int, int, int] = Config.DEFAULT_GRID_COLOR,
                 label_color: Tuple[int, int, int] = Config.DEFAULT_LABEL_COLOR,
                 line_width: int = Config.DEFAULT_LINE_WIDTH,
                 show_labels: bool = True):
        """
        Initialize gridline generator
        
        Args:
            h_spacing: Horizontal spacing between lines (pixels)
            v_spacing: Vertical spacing between lines (pixels)
            grid_color: RGB color for grid lines
            label_color: RGB color for coordinate labels
            line_width: Width of grid lines
            show_labels: Whether to show coordinate labels
        """
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing
        self.grid_color = grid_color
        self.label_color = label_color
        self.line_width = line_width
        self.show_labels = show_labels
    
    def add_gridlines(self, image: Image.Image) -> Image.Image:
        """
        Add gridlines to image
        
        Args:
            image: PIL Image to add gridlines to
            
        Returns:
            New image with gridlines
        """
        img_with_grid = image.copy()
        draw = ImageDraw.Draw(img_with_grid)
        
        width, height = image.size
        
        # Load font for labels
        try:
            font = ImageFont.truetype("arial.ttf", Config.LABEL_FONT_SIZE)
        except:
            font = ImageFont.load_default()
        
        # Draw vertical lines
        x = 0
        while x <= width:
            # Draw line
            draw.line([(x, 0), (x, height)], 
                     fill=self.grid_color, 
                     width=self.line_width)
            
            # Draw label
            if self.show_labels and x > 0:
                label = str(x)
                # Top label
                draw.text((x + Config.LABEL_OFFSET, Config.LABEL_OFFSET), 
                         label, 
                         fill=self.label_color, 
                         font=font)
                # Bottom label
                draw.text((x + Config.LABEL_OFFSET, height - 15), 
                         label, 
                         fill=self.label_color, 
                         font=font)
            
            x += self.v_spacing
        
        # Draw horizontal lines
        y = 0
        while y <= height:
            # Draw line
            draw.line([(0, y), (width, y)], 
                     fill=self.grid_color, 
                     width=self.line_width)
            
            # Draw label
            if self.show_labels and y > 0:
                label = str(y)
                # Left label
                draw.text((Config.LABEL_OFFSET, y + Config.LABEL_OFFSET), 
                         label, 
                         fill=self.label_color, 
                         font=font)
                # Right label
                draw.text((width - 30, y + Config.LABEL_OFFSET), 
                         label, 
                         fill=self.label_color, 
                         font=font)
            
            y += self.h_spacing
        
        return img_with_grid


# ============================================================================
# PDF GENERATOR
# ============================================================================

class PDFGeneratorWithGrid:
    """Generate PDF with gridlines"""
    
    @staticmethod
    def create_pdf_with_grid(images_with_grid: List[Image.Image]) -> BytesIO:
        """
        Create PDF from images with gridlines
        
        Args:
            images_with_grid: List of images with gridlines
            
        Returns:
            BytesIO containing PDF
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab required")
        
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        page_width, page_height = letter
        
        for img in images_with_grid:
            img_reader = ImageReader(img)
            img_width, img_height = img.size
            
            # Calculate scaling to fit page
            scale = min(page_width / img_width, page_height / img_height)
            scaled_width = img_width * scale
            scaled_height = img_height * scale
            
            # Center on page
            x_offset = (page_width - scaled_width) / 2
            y_offset = (page_height - scaled_height) / 2
            
            # Draw image
            c.drawImage(img_reader, x_offset, y_offset,
                       width=scaled_width, height=scaled_height)
            
            c.showPage()
        
        c.save()
        pdf_buffer.seek(0)
        return pdf_buffer


# ============================================================================
# FILE UTILITIES
# ============================================================================

class FileUtils:
    """File utilities"""
    
    @staticmethod
    def create_zip(files: List[BytesIO], filenames: List[str]) -> BytesIO:
        """Create zip file"""
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_data, filename in zip(files, filenames):
                zip_file.writestr(filename, file_data.getvalue())
        
        zip_buffer.seek(0)
        return zip_buffer


# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state():
    """Initialize session state"""
    defaults = {
        'pdf_images': None,
        'pdf_info': None,
        'pdf_filename': None,
        'images_with_grid': None,
        'current_page': 0
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_header():
    """Render header"""
    st.title("📐 PDF Gridline Generator")
    st.markdown("""
    Add coordinate gridlines to your PDF to help identify field positions.
    Perfect for creating templates for the Form Filler app!
    """)


def render_upload_section():
    """Render PDF upload section"""
    st.header("Step 1: Upload PDF")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        pdf_file = st.file_uploader(
            "Upload PDF file",
            type=['pdf'],
            key='pdf_upload'
        )
        
        if pdf_file:
            st.session_state.pdf_filename = pdf_file.name
            
            with st.spinner("Processing PDF..."):
                pdf_bytes = pdf_file.read()
                
                # Convert to images
                processor = PDFProcessor()
                images = processor.pdf_to_images(pdf_bytes)
                st.session_state.pdf_images = images
                
                # Get PDF info
                pdf_info = processor.get_pdf_info(pdf_bytes)
                st.session_state.pdf_info = pdf_info
                
                st.success(f"✓ Loaded {len(images)} pages")
    
    with col2:
        if st.session_state.pdf_info:
            st.metric("Pages", st.session_state.pdf_info['page_count'])


def render_grid_settings():
    """Render grid configuration section"""
    if not st.session_state.pdf_images:
        return
    
    st.header("Step 2: Configure Gridlines")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Spacing")
        
        h_spacing = st.number_input(
            "Horizontal Spacing (pixels)",
            min_value=10,
            max_value=500,
            value=Config.DEFAULT_H_SPACING,
            step=10,
            help="Distance between horizontal gridlines"
        )
        
        v_spacing = st.number_input(
            "Vertical Spacing (pixels)",
            min_value=10,
            max_value=500,
            value=Config.DEFAULT_V_SPACING,
            step=10,
            help="Distance between vertical gridlines"
        )
    
    with col2:
        st.subheader("Appearance")
        
        line_width = st.slider(
            "Line Width",
            min_value=1,
            max_value=5,
            value=Config.DEFAULT_LINE_WIDTH
        )
        
        show_labels = st.checkbox(
            "Show Coordinate Labels",
            value=True,
            help="Display coordinate numbers on gridlines"
        )
        
        grid_opacity = st.slider(
            "Grid Opacity",
            min_value=50,
            max_value=255,
            value=200,
            help="Higher = more transparent"
        )
    
    # Color based on opacity
    grid_color = (grid_opacity, grid_opacity, grid_opacity)
    label_color = (max(0, grid_opacity - 100), max(0, grid_opacity - 100), max(0, grid_opacity - 100))
    
    return {
        'h_spacing': h_spacing,
        'v_spacing': v_spacing,
        'grid_color': grid_color,
        'label_color': label_color,
        'line_width': line_width,
        'show_labels': show_labels
    }


def render_preview_section(grid_settings: dict):
    """Render preview section"""
    if not st.session_state.pdf_images or not grid_settings:
        return
    
    st.header("Step 3: Preview")
    
    images = st.session_state.pdf_images
    
    # Page selector
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        current_page = st.number_input(
            "Page",
            min_value=0,
            max_value=len(images) - 1,
            value=st.session_state.current_page,
            key='page_selector'
        )
        st.session_state.current_page = current_page
    
    with col2:
        st.info(f"📄 Page {current_page + 1} of {len(images)}")
    
    with col3:
        if st.button("🔄 Refresh Preview", use_container_width=True):
            st.rerun()
    
    # Generate preview
    with st.spinner("Generating preview..."):
        generator = GridlineGenerator(
            h_spacing=grid_settings['h_spacing'],
            v_spacing=grid_settings['v_spacing'],
            grid_color=grid_settings['grid_color'],
            label_color=grid_settings['label_color'],
            line_width=grid_settings['line_width'],
            show_labels=grid_settings['show_labels']
        )
        
        preview_image = generator.add_gridlines(images[current_page])
        
        st.image(preview_image, 
                caption=f"Page {current_page + 1} with gridlines", 
                use_container_width=True)
        
        # Image info
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Image Width", f"{preview_image.width} px")
        with col2:
            st.metric("Image Height", f"{preview_image.height} px")


def render_generation_section(grid_settings: dict):
    """Render generation section"""
    if not st.session_state.pdf_images or not grid_settings:
        return
    
    st.header("Step 4: Generate PDF with Gridlines")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        generate_all = st.checkbox(
            "Generate All Pages",
            value=True,
            help="Generate gridlines for all pages or just current page"
        )
    
    with col2:
        include_original = st.checkbox(
            "Include Original PDF",
            value=False,
            help="Include original PDF without gridlines in download"
        )
    
    if st.button("🚀 Generate PDF", type="primary", use_container_width=True):
        generate_pdf(grid_settings, generate_all, include_original)


def generate_pdf(grid_settings: dict, generate_all: bool, include_original: bool):
    """Generate PDF with gridlines"""
    images = st.session_state.pdf_images
    
    with st.spinner("Generating PDF with gridlines..."):
        # Create generator
        generator = GridlineGenerator(
            h_spacing=grid_settings['h_spacing'],
            v_spacing=grid_settings['v_spacing'],
            grid_color=grid_settings['grid_color'],
            label_color=grid_settings['label_color'],
            line_width=grid_settings['line_width'],
            show_labels=grid_settings['show_labels']
        )
        
        # Generate images with gridlines
        if generate_all:
            progress = st.progress(0)
            images_with_grid = []
            
            for idx, img in enumerate(images):
                img_with_grid = generator.add_gridlines(img)
                images_with_grid.append(img_with_grid)
                progress.progress((idx + 1) / len(images))
            
            st.session_state.images_with_grid = images_with_grid
        else:
            current_page = st.session_state.current_page
            img_with_grid = generator.add_gridlines(images[current_page])
            images_with_grid = [img_with_grid]
        
        # Create PDF
        pdf_with_grid = PDFGeneratorWithGrid.create_pdf_with_grid(images_with_grid)
        
        st.success(f"✅ Generated PDF with {len(images_with_grid)} pages!")
        
        # Download options
        col1, col2 = st.columns(2)
        
        base_filename = st.session_state.pdf_filename.replace('.pdf', '')
        
        with col1:
            st.download_button(
                label="📥 Download PDF with Gridlines",
                data=pdf_with_grid,
                file_name=f"{base_filename}_with_gridlines.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        
        if include_original:
            with col2:
                # Note: Would need original PDF bytes stored in session state
                st.info("Original PDF option requires storing PDF bytes")


def render_tips_section():
    """Render tips and instructions"""
    with st.expander("💡 Tips for Using Gridlines"):
        st.markdown("""
        ### How to Use This Tool
        
        1. **Upload your PDF form** - The form you want to create a template for
        
        2. **Set gridline spacing** - Smaller spacing (25-50px) gives more precision, 
           larger spacing (75-100px) is cleaner
        
        3. **Preview the gridlines** - Check different pages to ensure gridlines are visible
        
        4. **Generate PDF** - Download the PDF with gridlines
        
        5. **Find coordinates** - Use the gridline numbers to identify field positions:
           - X coordinate = vertical line number
           - Y coordinate = horizontal line number
        
        6. **Create template CSV** - Use these coordinates in your template CSV for the Form Filler app
        
        ### Example Template CSV
        ```csv
        field_name,page_number,x,y,field_type,font_size
        Full Name,0,150,200,text,10
        Email,0,150,250,text,10
        Amount,0,400,300,number,10
        ```
        
        ### Tips
        - Use **50px spacing** as a good starting point
        - Enable **coordinate labels** to easily read positions
        - Adjust **opacity** if gridlines obscure form content
        - Generate **all pages** if your form is multi-page
        """)


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main application"""
    st.set_page_config(**Config.PAGE_CONFIG)
    init_session_state()
    
    render_header()
    
    render_upload_section()
    
    st.divider()
    
    grid_settings = render_grid_settings()
    
    if grid_settings:
        st.divider()
        render_preview_section(grid_settings)
        
        st.divider()
        render_generation_section(grid_settings)
    
    st.divider()
    render_tips_section()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    📐 **Gridline Generator** - Create coordinate grids on PDFs to help identify field positions for form filling.
    """)


if __name__ == "__main__":
    main()