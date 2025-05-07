from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, AnyHttpUrl, ValidationError
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, Any, List
from requests.exceptions import RequestException
import base64
import pdfkit
import asyncio
from pyppeteer import launch
from PIL import Image
import io
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables")
    raise ValueError("GEMINI_API_KEY not found in environment variables")

try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    logger.info("Gemini API configured successfully")
except Exception as e:
    logger.error(f"Error configuring Gemini API: {str(e)}")
    raise

# FastAPI app
app = FastAPI(title="Website Analyzer API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class WebsiteRequest(BaseModel):
    url: AnyHttpUrl

# Response models
class SiteData(BaseModel):
    title: str
    meta_description: str
    headers: List[str]
    header_types: List[str]
    images: List[Dict[str, str]]
    links: List[str]
    content: str
    status_code: int
    url: str
    word_count: int
    image_count: int
    link_count: int
    h1_count: int
    alt_text_coverage: float
    cta_count: int
    form_count: int
    full_screenshot: Optional[str] = None
    header_screenshot: Optional[str] = None
    nav_screenshot: Optional[str] = None
    main_screenshot: Optional[str] = None
    footer_screenshot: Optional[str] = None

class Scores(BaseModel):
    user_experience: int
    content_effectiveness: int
    conversion_optimization: int
    visual_design: int
    business_alignment: int
    content_analysis: Dict[str, int]

class AnalysisResponse(BaseModel):
    site_data: SiteData
    analysis: str
    scores: Scores
    summary: str
    pdf_base64: Optional[str] = None

# Async function to take screenshots
async def take_screenshot(url, selector=None, timeout=30000):
    browser = await launch(headless=True)
    page = await browser.newPage()
    try:
        await page.goto(url, {'waitUntil': 'networkidle0', 'timeout': timeout})
        if selector:
            element = await page.waitForSelector(selector, {'timeout': timeout})
            if not element:
                return None
            screenshot = await element.screenshot()
        else:
            screenshot = await page.screenshot()
        return screenshot
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return None
    finally:
        await browser.close()

# Web scraping function
async def scrape_website(url: str) -> dict:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        logger.info(f"Scraping website: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract key elements
        title = soup.title.string.strip() if soup.title and soup.title.string else 'No title'
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_description = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else 'No meta description'
        
        headers = []
        header_types = []
        for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            headers.append(h.get_text().strip())
            header_types.append(h.name)
        
        images = [{'src': img['src'], 'alt': img.get('alt', '')} for img in soup.find_all('img') if img.get('src')]
        
        links = [a['href'] for a in soup.find_all('a') if a.get('href')]
        
        # Clean content text - remove excessive whitespace
        content = ' '.join(soup.get_text().split())
        
        # Build data dictionary
        data = {
            'title': title,
            'meta_description': meta_description,
            'headers': headers,
            'header_types': header_types,
            'images': images,
            'links': links,
            'content': content[:10000],
            'status_code': response.status_code,
            'url': url
        }
        
        # Additional SEO metrics
        data['word_count'] = len(data['content'].split())
        data['image_count'] = len(data['images'])
        data['link_count'] = len(data['links'])
        data['h1_count'] = len([h for h in soup.find_all('h1')])
        data['alt_text_coverage'] = (len([img for img in data['images'] if img['alt']]) / 
                                     max(data['image_count'], 1)) * 100
        
        # New metrics for conversion optimization
        cta_keywords = ['contact', 'signup', 'register', 'buy', 'order', 'get started', 'download']
        data['cta_count'] = len([link for link in data['links'] if any(keyword in link.lower() for keyword in cta_keywords)])
        data['form_count'] = len(soup.find_all('form'))
        
        # Capture screenshots of key elements
        try:
            # Full page screenshot
            full_screenshot = await take_screenshot(url)
            if full_screenshot:
                data['full_screenshot'] = base64.b64encode(full_screenshot).decode('utf-8')
            
            # Header screenshot
            header_screenshot = await take_screenshot(url, 'header, .header, #header')
            if header_screenshot:
                data['header_screenshot'] = base64.b64encode(header_screenshot).decode('utf-8')
            
            # Navigation screenshot
            nav_screenshot = await take_screenshot(url, 'nav, .nav, #nav, .navbar, #navbar')
            if nav_screenshot:
                data['nav_screenshot'] = base64.b64encode(nav_screenshot).decode('utf-8')
            
            # Main content screenshot
            main_screenshot = await take_screenshot(url, 'main, .main, #main, .content, #content')
            if main_screenshot:
                data['main_screenshot'] = base64.b64encode(main_screenshot).decode('utf-8')
            
            # Footer screenshot
            footer_screenshot = await take_screenshot(url, 'footer, .footer, #footer')
            if footer_screenshot:
                data['footer_screenshot'] = base64.b64encode(footer_screenshot).decode('utf-8')
        except Exception as e:
            logger.error(f"Error capturing screenshots: {str(e)}")
        
        logger.info(f"Successfully scraped website: {url}")
        return data
    
    except RequestException as e:
        logger.error(f"Request error scraping {url}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                           detail=f"Error accessing website {url}: {str(e)}")
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                           detail=f"Error scraping {url}: {str(e)}")

# Function to generate analysis focusing on functional aspects
def generate_analysis(site_data: dict) -> str:
    prompt = f"""
    Act as a senior conversion rate optimization specialist with 15 years of experience in user experience design and business strategy. Conduct a functional analysis of {site_data['url']} focusing on user journey, content effectiveness, and business impact across these domains:

    1. User Experience & Journey
    - First impression and value proposition clarity
    - Navigation intuitiveness and user flow
    - Mobile experience and responsiveness
    - Form usability and conversion friction
    - Trust elements and credibility indicators

    2. Content Effectiveness
    - Message clarity and relevance
    - Content structure and scannability
    - Call-to-action effectiveness
    - Value proposition communication
    - Content alignment with user needs

    3. Visual Design & Hierarchy
    - Visual appeal and brand consistency
    - Information hierarchy effectiveness
    - Use of whitespace and visual breathing room
    - Color psychology and emotional impact
    - Visual guidance of user attention

    4. Conversion Optimization
    - Lead generation effectiveness
    - Conversion path efficiency
    - Exit intent strategies
    - Personalization opportunities
    - A/B testing opportunities

    5. Business Alignment
    - Alignment with business objectives
    - Revenue generation effectiveness
    - Customer retention elements
    - Upsell/cross-sell opportunities
    - Customer journey mapping

    Based on the website data provided, give specific functional recommendations for improvement. Focus on user experience, content effectiveness, and business impact.
    
    Here is some information about the website:
    Title: {site_data['title']}
    Meta Description: {site_data['meta_description']}
    Word Count: {site_data['word_count']}
    Number of Images: {site_data['image_count']}
    Alt Text Coverage: {site_data['alt_text_coverage']:.1f}%
    Number of Links: {site_data['link_count']}
    Number of CTA Links: {site_data['cta_count']}
    Number of Forms: {site_data['form_count']}
    H1 Tags Count: {site_data['h1_count']}
    Headers: {', '.join(site_data['headers'][:10])}
    
    Provide a comprehensive report with specific functional recommendations for improvement, focusing on user experience, content effectiveness, and business impact.
    """
    
    try:
        logger.info(f"Generating analysis for {site_data['url']}")
        response = model.generate_content(prompt)
        analysis = response.text
        logger.info(f"Successfully generated analysis")
        return analysis
    except Exception as e:
        logger.error(f"Error generating analysis: {str(e)}")
        return "Error generating detailed analysis. Please try again later."

# Function to calculate scores focusing on functional aspects
def calculate_scores(site_data: dict) -> dict:
    logger.info("Calculating scores")
    scores = {
        'user_experience': 0,
        'content_effectiveness': 0,
        'conversion_optimization': 0,
        'visual_design': 0,
        'business_alignment': 0,
        'content_analysis': {
            'performance': 0,
            'seo': 0,
            'ux': 0,
            'security': 0
        }
    }
    
    # User Experience Score
    user_experience = 0
    if len(site_data['title']) > 10 and len(site_data['title']) < 70:
        user_experience += 20
    if site_data['h1_count'] == 1:
        user_experience += 20
    if site_data['alt_text_coverage'] > 50:
        user_experience += 15
    scores['user_experience'] = min(100, user_experience)
    
    # Content Effectiveness Score
    content_effectiveness = 0
    if len(site_data['meta_description']) > 50 and len(site_data['meta_description']) < 160:
        content_effectiveness += 25
    if site_data['word_count'] > 300:
        content_effectiveness += 25
    unique_header_levels = len(set(site_data['header_types']))
    content_effectiveness += min(30, unique_header_levels * 10)
    scores['content_effectiveness'] = min(100, content_effectiveness)
    
    # Conversion Optimization Score
    conversion_optimization = 0
    conversion_optimization += min(30, site_data['cta_count'] * 10)
    conversion_optimization += min(20, site_data['form_count'] * 10)
    scores['conversion_optimization'] = min(100, conversion_optimization)
    
    # Visual Design Score
    visual_design = 0
    visual_design += min(40, int(site_data['alt_text_coverage'] * 0.5))
    visual_design += min(30, int(site_data['image_count'] * 2))
    scores['visual_design'] = min(100, visual_design)
    
    # Business Alignment Score
    business_alignment = 0
    business_alignment += min(30, int(site_data['link_count'] * 0.5))
    business_alignment += min(20, int(site_data['word_count'] / 100))
    scores['business_alignment'] = min(100, business_alignment)
    
    # Content Analysis Metrics
    content_analysis = scores['content_analysis']
    
    # Performance Score
    performance_score = min(100, int((site_data['alt_text_coverage'] * 0.7) + (site_data['image_count'] * 0.3)))
    content_analysis['performance'] = performance_score
    
    # SEO Score
    seo_score = 0
    if len(site_data['title']) > 10 and len(site_data['title']) < 70:
        seo_score += 40
    if len(site_data['meta_description']) > 50 and len(site_data['meta_description']) < 160:
        seo_score += 40
    if site_data['h1_count'] == 1:
        seo_score += 20
    content_analysis['seo'] = min(100, seo_score)
    
    # UX Score
    ux_score = 0
    if site_data['h1_count'] == 1:
        ux_score += 30
    if site_data['word_count'] > 300:
        ux_score += 30
    unique_header_levels = len(set(site_data['header_types']))
    ux_score += min(40, unique_header_levels * 10)
    content_analysis['ux'] = min(100, ux_score)
    
    # Security Score (basic implementation)
    security_score = 0
    content_analysis['security'] = security_score
    
    return scores

# Function to generate non-technical summary
def generate_summary(analysis: str, scores: dict) -> str:
    try:
        logger.info("Generating summary")
        summary = f"""
        # Summary of Recommended Actions
        
        ## User Experience Score: {scores['user_experience']}%
        - Improve navigation clarity
        - Enhance mobile responsiveness
        - Optimize first impression
        
        ## Content Effectiveness Score: {scores['content_effectiveness']}%
        - Strengthen value proposition
        - Improve content structure
        - Enhance call-to-action effectiveness
        
        ## Conversion Optimization Score: {scores['conversion_optimization']}%
        - Reduce conversion friction
        - Implement exit intent strategies
        - Personalize user experience
        
        ## Visual Design Score: {scores['visual_design']}%
        - Improve visual hierarchy
        - Enhance color psychology
        - Optimize whitespace usage
        
        ## Business Alignment Score: {scores['business_alignment']}%
        - Align content with business objectives
        - Improve revenue generation paths
        - Implement customer journey mapping
        
        These recommendations are prioritized based on potential impact. Start with user experience and content effectiveness for quick wins.
        """
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return "Error generating summary. Please see the detailed analysis for recommendations."

# Function to generate HTML report for PDF
def generate_html_report(site_data: dict, analysis: str, scores: dict, summary: str) -> str:
    try:
        logger.info("Generating HTML report")
        # Escape any potentially problematic HTML
        title = site_data['title'].replace("<", "&lt;").replace(">", "&gt;")
        meta_description = site_data['meta_description'].replace("<", "&lt;").replace(">", "&gt;")
        
        # Process analysis and summary to ensure proper HTML formatting
        analysis_html = analysis.replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
        summary_html = summary.replace("\n", "<br>")
        
        content_analysis = scores.get('content_analysis', {
            'performance': 0,
            'seo': 0,
            'ux': 0,
            'security': 0
        })
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>CRO Analysis Report for {title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #000; background-color: #fff; }}
                h1 {{ color: #2c3e50; margin-top: 20px; }}
                h2 {{ color: #34495e; margin-top: 15px; }}
                h3 {{ color: #3498db; }}
                p {{ margin-bottom: 10px; }}
                .metric {{ margin: 20px 0; }}
                .recommendation {{ margin: 15px 0; padding: 15px; background: #f8f9fa; border-left: 4px solid #3498db; }}
                .score {{ font-weight: bold; color: #2c3e50; }}
                .score-container {{ display: flex; align-items: center; margin-bottom: 10px; }}
                .score-label {{ width: 150px; }}
                .score-bar-container {{ width: 200px; height: 15px; background-color: #eee; margin-right: 10px; }}
                .score-bar {{ height: 15px; display: block; }}
                .header {{ background-color: #3498db; color: white; padding: 20px; margin-bottom: 20px; }}
                .footer {{ margin-top: 30px; text-align: center; font-size: 12px; color: #7f8c8d; }}
                .screenshot-container {{ margin: 20px 0; }}
                .screenshot {{ max-width: 100%; height: auto; }}
                .content-analysis-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                .content-analysis-table th, .content-analysis-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .content-analysis-table th {{ background-color: #f2f2f2; }}
                .improvement-section {{ margin-bottom: 30px; }}
                .complexity-tag {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 12px; }}
                .easy {{ background-color: #dff0d8; color: #3c763d; }}
                .medium {{ background-color: #fcf8e3; color: #8a6d3b; }}
                .hard {{ background-color: #f2dede; color: #a94442; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Website Analysis Report</h1>
                <p>Generated on {os.popen('date').read().strip()}</p>
            </div>
            
            <h2>Website Analysis: {title}</h2>
            
            <h3>Basic Information</h3>
            <p><strong>URL:</strong> {site_data['url']}</p>
            <p><strong>Title:</strong> {title}</p>
            <p><strong>Meta Description:</strong> {meta_description}</p>
            <p><strong>Word Count:</strong> {site_data['word_count']}</p>
            <p><strong>Images:</strong> {site_data['image_count']}</p>
            <p><strong>Links:</strong> {site_data['link_count']}</p>
            <p><strong>CTA Links:</strong> {site_data['cta_count']}</p>
            <p><strong>Forms:</strong> {site_data['form_count']}</p>
            <p><strong>H1 Tags:</strong> {site_data['h1_count']}</p>
            <p><strong>Alt Text Coverage:</strong> {site_data['alt_text_coverage']:.1f}%</p>
            
            <h3>Functional Scores</h3>
            
            <div class="score-container">
                <div class="score-label">User Experience:</div>
                <div class="score-bar-container">
                    <div class="score-bar" style="width: {scores['user_experience']}%; background-color: {'#27ae60' if scores['user_experience'] > 80 else '#f39c12' if scores['user_experience'] > 50 else '#e74c3c'};"></div>
                </div>
                <div class="score">{scores['user_experience']}%</div>
            </div>
            
            <div class="score-container">
                <div class="score-label">Content Effectiveness:</div>
                <div class="score-bar-container">
                    <div class="score-bar" style="width: {scores['content_effectiveness']}%; background-color: {'#27ae60' if scores['content_effectiveness'] > 80 else '#f39c12' if scores['content_effectiveness'] > 50 else '#e74c3c'};"></div>
                </div>
                <div class="score">{scores['content_effectiveness']}%</div>
            </div>
            
            <div class="score-container">
                <div class="score-label">Conversion Optimization:</div>
                <div class="score-bar-container">
                    <div class="score-bar" style="width: {scores['conversion_optimization']}%; background-color: {'#27ae60' if scores['conversion_optimization'] > 80 else '#f39c12' if scores['conversion_optimization'] > 50 else '#e74c3c'};"></div>
                </div>
                <div class="score">{scores['conversion_optimization']}%</div>
            </div>
            
            <div class="score-container">
                <div class="score-label">Visual Design:</div>
                <div class="score-bar-container">
                    <div class="score-bar" style="width: {scores['visual_design']}%; background-color: {'#27ae60' if scores['visual_design'] > 80 else '#f39c12' if scores['visual_design'] > 50 else '#e74c3c'};"></div>
                </div>
                <div class="score">{scores['visual_design']}%</div>
            </div>
            
            <div class="score-container">
                <div class="score-label">Business Alignment:</div>
                <div class="score-bar-container">
                    <div class="score-bar" style="width: {scores['business_alignment']}%; background-color: {'#27ae60' if scores['business_alignment'] > 80 else '#f39c12' if scores['business_alignment'] > 50 else '#e74c3c'};"></div>
                </div>
                <div class="score">{scores['business_alignment']}%</div>
            </div>
            
            <h2>Content Analysis</h2>
            <table class="content-analysis-table">
                <tr>
                    <th>Category</th>
                    <th>Score (%)</th>
                </tr>
                <tr>
                    <td>Performance</td>
                    <td>{content_analysis['performance']}</td>
                </tr>
                <tr>
                    <td>SEO</td>
                    <td>{content_analysis['seo']}</td>
                </tr>
                <tr>
                    <td>UX</td>
                    <td>{content_analysis['ux']}</td>
                </tr>
                <tr>
                    <td>Security</td>
                    <td>{content_analysis['security']}</td>
                </tr>
            </table>
            
            <h2>Improvement Recommendations</h2>
            
            <div class="improvement-section">
                <h3>Header Section</h3>
                <div class="screenshot-container">
                    <img class="screenshot" src="data:image/png;base64,{site_data.get('header_screenshot', '')}" alt="Header screenshot">
                </div>
                <h4>Recommendations:</h4>
                <p>Simplify navigation menu and improve brand visibility</p>
                <span class="complexity-tag easy">Easy</span>
                <p>Implement sticky header for better user experience</p>
                <span class="complexity-tag medium">Medium</span>
            </div>
            
            <div class="improvement-section">
                <h3>Navigation Menu</h3>
                <div class="screenshot-container">
                    <img class="screenshot" src="data:image/png;base64,{site_data.get('nav_screenshot', '')}" alt="Navigation screenshot">
                </div>
                <h4>Recommendations:</h4>
                <p>Reduce number of menu items for better clarity</p>
                <span class="complexity-tag easy">Easy</span>
                <p>Implement mega-menu for complex navigation</p>
                <span class="complexity-tag hard">Hard</span>
            </div>
            
            <div class="improvement-section">
                <h3>Main Content Area</h3>
                <div class="screenshot-container">
                    <img class="screenshot" src="data:image/png;base64,{site_data.get('main_screenshot', '')}" alt="Main content screenshot">
                </div>
                <h4>Recommendations:</h4>
                <p>Improve content hierarchy with better headings</p>
                <span class="complexity-tag easy">Easy</span>
                <p>Optimize image loading speeds</p>
                <span class="complexity-tag medium">Medium</span>
            </div>
            
            <div class="improvement-section">
                <h3>Footer Section</h3>
                <div class="screenshot-container">
                    <img class="screenshot" src="data:image/png;base64,{site_data.get('footer_screenshot', '')}" alt="Footer screenshot">
                </div>
                <h4>Recommendations:</h4>
                <p>Add social media links and contact information</p>
                <span class="complexity-tag easy">Easy</span>
                <p>Implement footer search functionality</p>
                <span class="complexity-tag hard">Hard</span>
            </div>
            
            <h2>Actionable Summary</h2>
            <div class="recommendation">
                {summary_html}
            </div>
            
            <h2>Detailed Analysis</h2>
            <div class="recommendation">
                {analysis_html}
            </div>
            
            <div class="footer">
                <p>Generated by Website Analyzer API | Powered by AI</p>
            </div>
        </body>
        </html>
        """
        return html
    except Exception as e:
        logger.error(f"Error generating HTML: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating HTML: {str(e)}")

# Function to generate PDF using WeasyPrint
def generate_pdf(html_content: str) -> Optional[str]:
    try:
        logger.info("Generating PDF using pdfkit")
        # Convert HTML to PDF bytes
        pdf_bytes = pdfkit.from_string(html_content, False)
        
        # Convert PDF to base64 for transmission
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        return pdf_base64
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return None

# API endpoint to analyze website
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_website(request: WebsiteRequest):
    try:
        logger.info(f"Received analyze request for URL: {request.url}")
        
        # Scrape website data
        site_data = await scrape_website(str(request.url))
        
        # Generate analysis
        analysis = generate_analysis(site_data)
        scores = calculate_scores(site_data)
        summary = generate_summary(analysis, scores)
        
        # Generate HTML report
        html_report = generate_html_report(site_data, analysis, scores, summary)
        
        # Generate PDF
        pdf_base64 = None
        if html_report:
            pdf_base64 = generate_pdf(html_report)
        
        # Return all data
        response_data = {
            "site_data": SiteData(**site_data),
            "analysis": analysis,
            "scores": Scores(**scores),
            "summary": summary,
            "pdf_base64": pdf_base64
        }
        
        logger.info(f"Successfully analyzed website: {request.url}")
        return response_data
        
    except ValidationError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(ve)}"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Server error: {str(e)}"
        )

# Health check endpoint
@app.get("/")
async def health_check():
    return {"status": "healthy", "message": "Website Analyzer API is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)