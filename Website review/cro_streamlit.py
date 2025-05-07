import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import pdfkit
import os

# Configure Gemini API
genai.configure(api_key="AIzaSyDXbkBPwC9LQ1Zbvfq4Hc1kyQVWalPxfZ4")
model = genai.GenerativeModel("gemini-1.5-flash")

# Web scraping function
def scrape_website(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract key elements
        data = {
            'title': soup.title.string.strip() if soup.title else 'No title',
            'meta_description': soup.find('meta', attrs={'name': 'description'})['content'].strip() if soup.find('meta', attrs={'name': 'description'}) else 'No meta description',
            'headers': [h.get_text().strip() for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])],
            'images': [{'src': img['src'], 'alt': img.get('alt', '')} for img in soup.find_all('img') if img.get('src')],
            'links': [a['href'] for a in soup.find_all('a') if a.get('href')],
            'content': soup.get_text().strip(),
            'status_code': response.status_code,
            'url': url
        }
        
        # Additional SEO metrics
        data['word_count'] = len(data['content'].split())
        data['image_count'] = len(data['images'])
        data['link_count'] = len(data['links'])
        data['h1_count'] = len([h for h in data['headers'] if h.startswith('<h1')])
        data['alt_text_coverage'] = len([img for img in data['images'] if img['alt']]) / data['image_count'] if data['image_count'] > 0 else 0

        return data
    
    except Exception as e:
        st.error(f"Error scraping {url}: {str(e)}")
        return None

# Function to generate analysis
def generate_analysis(site_data):
    prompt = f"""
    Act as a senior website optimization architect with 15 years of experience in technical SEO, UX engineering, and conversion rate optimization. Conduct a forensic analysis of {site_data['url']} using these 143 evaluation parameters across 7 core domains:

    1. Performance & Speed Audit
    Test LCP <1.2s, FID <100ms, CLS <0.1 using Lighthouse v12
    Verify HTTP/3 implementation and 0-RTT connection status
    Audit image compression ratios (WebP/AVIF adoption >95%)
    Check font loading strategy (font-display: swap + preloading)
    Validate cache hit ratio (>85% static assets cached via CDN)
    Critical rendering path optimization status
    Tools: WebPageTest Enterprise, Chrome UX Report, Cloudflare Radar

    2. SEO & Technical Architecture
    Crawl budget efficiency (orphan pages <5%)
    Schema markup coverage (90%+ pages with structured data)
    Internal link equity distribution (PR flow analysis)
    XML sitemap integrity (100% indexable pages included)
    Canonicalization accuracy (0 duplicate content clusters)
    hreflang implementation (geo-targeting precision)
    Innovation Check: AI-generated content enrichment, predictive internal linking

    3. UI/UX Design Evaluation
    Scroll depth heatmaps (75%+ completion rate)
    Gesture navigation fluidity (swipe/touch response <80ms)
    Cognitive load score (Hick's Law compliance)
    F-pattern/Z-pattern alignment (eye-tracking optimization)
    Contrast ratio compliance (WCAG AAA standards)
    Micro-interaction polish (hover states, loading animations)
    Emerging Tech: Spatial UI patterns, AR preview integration

    4. Content & Accessibility
    Readability score (Flesch >70 + GPT-4 coherence analysis)
    Alt-text density (100% images + AI-generated context)
    Dynamic content personalization (ML-driven variants)
    Voice navigation readiness (screen reader compatibility)
    Localization depth (52 language support check)
    2025 Must-Have: Real-time content updates via WebSocket

    5. Security & Compliance
    TLS 1.3 implementation (0 legacy ciphers)
    CSP header strictness (nonce/hash-based policies)
    GDPR/CCPA automation (preference center integration)
    Bot mitigation efficacy (CAPTCHA-free solutions)
    Cutting Edge: Quantum-resistant cryptography audit

    6. Conversion Architecture
    Exit-intent prediction accuracy (>40% save rate)
    Form abandonment root cause analysis
    Price anchoring effectiveness (psychographic alignment)
    Trust signal density (security badges/media mentions)
    Pro Tactics: Neurodesign principles for CTA placement

    7. Emerging Trends Integration
    WebGL 3.0 implementation status
    WebAssembly module adoption
    Predictive pre-fetching algorithms
    AI-generated layout variants (A/B test ready)

    Deliverables:
    Priority matrix (P0-P3 issues)
    Technical debt quantification
    Competitor gap analysis
    Personalization roadmap
    12-month optimization calendar

    Data Sources:
    Google Search Console (20+ data dimensions)
    FullStory session replays
    MarketMuse content gap analysis
    SEMrush Sensor volatility tracking

    Based on this analysis, provide a comprehensive report with specific recommendations for improvement.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating analysis: {str(e)}"

# Function to calculate scores
def calculate_scores(site_data):
    scores = {
        'performance': 0,
        'seo': 0,
        'ux': 0,
        'content': 0,
        'security': 0,
        'conversion': 0,
        'emerging_trends': 0
    }
    
    # Example scoring logic (you would need to implement actual scoring based on analysis)
    scores['performance'] = min(100, int(site_data['word_count'] / 1000 * 30))
    scores['seo'] = min(100, int(site_data['image_count'] * 2))
    scores['ux'] = min(100, int(site_data['alt_text_coverage'] * 100))
    scores['content'] = min(100, int(len(site_data['headers']) * 2))
    scores['security'] = 50  # Placeholder
    scores['conversion'] = 40  # Placeholder
    scores['emerging_trends'] = 30  # Placeholder
    
    return scores

# Function to generate non-technical summary
def generate_summary(analysis, scores):
    try:
        # Create a non-technical summary based on scores
        summary = f"""
        # Summary of Recommended Actions
        
        ## Performance Improvements ({scores['performance']}%)
        - Optimize website loading speed for better user experience
        - Compress images and leverage browser caching
        
        ## SEO Enhancements ({scores['seo']}%)
        - Improve meta descriptions and title tags
        - Fix broken links and optimize internal linking
        
        ## User Experience Upgrades ({scores['ux']}%)
        - Enhance mobile responsiveness
        - Improve navigation clarity and visual hierarchy
        
        ## Content Optimization ({scores['content']}%)
        - Add missing header tags (H1, H2, etc.)
        - Improve alt text for images
        
        ## Security Upgrades ({scores['security']}%)
        - Implement modern security protocols
        - Improve data protection measures
        
        ## Conversion Rate Optimization
        - Implement clear call-to-action buttons
        - Improve form design and reduce abandonment
        
        ## Emerging Trends Adoption
        - Consider implementing AI-driven personalization
        - Explore advanced loading techniques for faster interactions
        
        These recommendations are prioritized based on potential impact. Start with performance and SEO improvements for quick wins.
        """
        return summary
    except Exception as e:
        return f"Error generating summary: {str(e)}"

# Function to generate HTML content for PDF
def generate_html_report(site_data, analysis, scores, summary):
    try:
        html = f"""
        <html>
        <head>
            <title>CRO Analysis Report for {site_data['title'] if site_data else 'Website'}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; }}
                p {{ line-height: 1.6; }}
                .metric {{ margin: 20px 0; }}
                .recommendation {{ margin: 30px 0; padding: 20px; background: #f8f9fa; border-left: 4px solid #3498db; }}
            </style>
        </head>
        <body>
            <h1>CRO Analysis Report</h1>
            <h2>Website: {site_data['title'] if site_data else 'Website'}</h2>
            
            <p>This tool analyzes websites and provides conversion rate optimization (CRO) recommendations using AI.</p>
            
            <h2>Analysis Results</h2>
            
            <h3>Basic Information</h3>
            <p><strong>Title:</strong> {site_data['title']}</p>
            <p><strong>Meta Description:</strong> {site_data['meta_description']}</p>
            <p><strong>Word Count:</strong> {site_data['word_count']}</p>
            <p><strong>Images:</strong> {site_data['image_count']}</p>
            <p><strong>Links:</strong> {site_data['link_count']}</p>
            <p><strong>H1 Tags:</strong> {site_data['h1_count']}</p>
            <p><strong>Alt Text Coverage:</strong> {site_data['alt_text_coverage']:.1f}%</p>
            
            <h3>Content Analysis</h3>
            <p><strong>Performance Score:</strong> {scores['performance']}%</p>
            <p><strong>SEO Score:</strong> {scores['seo']}%</p>
            <p><strong>UX Score:</strong> {scores['ux']}%</p>
            <p><strong>Content Score:</strong> {scores['content']}%</p>
            <p><strong>Security Score:</strong> {scores['security']}%</p>
            
            <h2>AI Recommendations</h2>
            <div class="recommendations">
                {analysis.replace('\n', '<br>')}
            </div>
            
            <h2>Actionable Summary</h2>
            <div class="recommendations">
                {summary.replace('\n', '<br>')}
            </div>
        </body>
        </html>
        """
        return html
    except Exception as e:
        st.error(f"Error generating HTML: {str(e)}")
        return None

# Function to generate PDF
def generate_pdf(html_content):
    try:
        pdf = pdfkit.from_string(html_content, False)
        return pdf
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None

# Streamlit app
def main():
    st.title("CRO Expert: AI-Powered Website Analyzer")

    # Input for website URL
    url = st.text_input("Enter website URL to analyze:")

    # Button to analyze website
    if st.button("Analyze Website"):
        if url:
            with st.spinner("Analyzing website..."):
                # Scrape website data
                site_data = scrape_website(url)
                
                if not site_data:
                    st.error("Failed to scrape website. Please try another URL.")
                    return

                # Generate analysis
                analysis = generate_analysis(site_data)
                scores = calculate_scores(site_data)
                summary = generate_summary(analysis, scores)
                
                # Generate HTML report
                html_report = generate_html_report(site_data, analysis, scores, summary)
                if not html_report:
                    st.error("Failed to generate HTML report")
                    return

                # Display results
                st.header("Analysis Results")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Basic Information")
                    st.write(f"**Title:** {site_data['title']}")
                    st.write(f"**Meta Description:** {site_data['meta_description']}")
                    st.write(f"**Word Count:** {site_data['word_count']}")
                    st.write(f"**Images:** {site_data['image_count']}")
                    st.write(f"**Links:** {site_data['link_count']}")
                    st.write(f"**H1 Tags:** {site_data['h1_count']}")
                    st.write(f"**Alt Text Coverage:** {site_data['alt_text_coverage']:.1f}%")
                
                with col2:
                    st.subheader("Content Analysis")
                    st.metric("Performance Score", f"{scores['performance']}%")
                    st.metric("SEO Score", f"{scores['seo']}%")
                    st.metric("UX Score", f"{scores['ux']}%")
                    st.metric("Content Score", f"{scores['content']}%")
                    st.metric("Security Score", f"{scores['security']}%")

                st.header("AI Recommendations")
                st.write(analysis)

                st.header("Actionable Summary")
                st.write(summary)

                # Generate PDF
                pdf = generate_pdf(html_report)
                if pdf:
                    st.success("Report generated successfully!")
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf,
                        file_name="cro_analysis_report.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("Failed to generate PDF")
        else:
            st.error("Please enter a website URL.")

if __name__ == "__main__":
    main()