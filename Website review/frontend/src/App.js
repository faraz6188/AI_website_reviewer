import React, { useState, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { useReactToPrint } from 'react-to-print';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import './App.css';

function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  
  // Ref for printable content
  const printRef = useRef();

  // Handle print functionality with react-to-print
  const handlePrint = useReactToPrint({
    content: () => printRef.current,
    documentTitle: 'CRO Analysis Report',
    pageStyle: `
      @page { 
        size: A4; 
        margin: 20mm; 
      }
      @media print {
        body {
          -webkit-print-color-adjust: exact;
        }
        .print-container {
          width: 100%;
          max-width: 210mm;
          margin: 0 auto;
          font-family: Arial, sans-serif;
        }
        .score-item {
          display: flex;
          justify-content: space-between;
          margin-bottom: 10px;
          border-bottom: 1px solid #eee;
          padding-bottom: 5px;
        }
        .scores {
          display: flex;
          flex-wrap: wrap;
          justify-content: space-between;
        }
        .card {
          break-inside: avoid;
          margin-bottom: 20px;
        }
        .recommendations, .summary {
          break-inside: avoid;
          margin-top: 20px;
        }
      }
    `
  });

  // New function to download PDF
  const handleDownloadPDF = () => {
    const input = printRef.current;
    
    // Use html2canvas to capture the entire content
    html2canvas(input, { 
      scale: 2, 
      useCORS: true,
      logging: false,
      allowTaint: true 
    }).then((canvas) => {
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: 'p',
        unit: 'mm',
        format: 'a4'
      });

      // Get canvas dimensions
      const imgWidth = 210; // A4 width in mm
      const pageHeight = 297; // A4 height in mm
      const imgHeight = canvas.height * imgWidth / canvas.width;
      let heightLeft = imgHeight;
      let position = 0;

      // Add first page
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight, '', 'FAST');
      heightLeft -= pageHeight;

      // Add additional pages if content is longer than one page
      while (heightLeft >= 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight, '', 'FAST');
        heightLeft -= pageHeight;
      }

      // Save the PDF
      pdf.save('CRO_Analysis_Report.pdf');
    }).catch((err) => {
      console.error('Error creating PDF:', err);
      alert('Failed to generate PDF. Please try again.');
    });
  };

  const handleAnalyze = async () => {
    if (!url) {
      setError('Please enter a website URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('http://localhost:8000/analyze', { url });
      setResults(response.data);
    } catch (err) {
      setError('Failed to analyze website. Please try another URL.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>CRO Expert: AI-Powered Website Analyzer</h1>
      </header>

      <div className="input-section">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter website URL to analyze"
        />
        <button onClick={handleAnalyze} disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze Website'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Analyzing website...</p>
        </div>
      )}

      {results && (
        <div className="results">
          {/* Printable Content */}
          <div ref={printRef} className="print-container">
            <div className="basic-info">
              <h2>Analysis Results</h2>
              <div className="grid">
                <div className="card">
                  <h3>Basic Information</h3>
                  <p><strong>Title:</strong> {results.site_data.title}</p>
                  <p><strong>Meta Description:</strong> {results.site_data.meta_description}</p>
                  <p><strong>Word Count:</strong> {results.site_data.word_count}</p>
                  <p><strong>Images:</strong> {results.site_data.image_count}</p>
                  <p><strong>Links:</strong> {results.site_data.link_count}</p>
                  <p><strong>H1 Tags:</strong> {results.site_data.h1_count}</p>
                  <p><strong>Alt Text Coverage:</strong> {results.site_data.alt_text_coverage}%</p>
                </div>
                
                <div className="card">
                  <h3>Content Analysis</h3>
                  <div className="scores">
                    <div className="score-item">
                      <span>Performance</span>
                      <span className="score">{results.scores.performance}%</span>
                    </div>
                    <div className="score-item">
                      <span>SEO</span>
                      <span className="score">{results.scores.seo}%</span>
                    </div>
                    <div className="score-item">
                      <span>UX</span>
                      <span className="score">{results.scores.ux}%</span>
                    </div>
                    <div className="score-item">
                      <span>Content</span>
                      <span className="score">{results.scores.content}%</span>
                    </div>
                    <div className="score-item">
                      <span>Security</span>
                      <span className="score">{results.scores.security}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <h2>Improvement Recommendations</h2>
            
            <div className="improvement-section">
                <h3>Header Section</h3>
                <div className="screenshot-container">
                    {results.site_data.header_screenshot && (
                      <img 
                        className="screenshot" 
                        src={`data:image/png;base64,${results.site_data.header_screenshot}`} 
                        alt="Header screenshot" 
                      />
                    )}
                </div>
                <h4>Recommendations:</h4>
                <p>Simplify navigation menu and improve brand visibility</p>
                <span className="complexity-tag easy">Easy</span>
                <p>Implement sticky header for better user experience</p>
                <span className="complexity-tag medium">Medium</span>
            </div>
            
            <div className="improvement-section">
                <h3>Navigation Menu</h3>
                <div className="screenshot-container">
                    {results.site_data.nav_screenshot && (
                      <img 
                        className="screenshot" 
                        src={`data:image/png;base64,${results.site_data.nav_screenshot}`} 
                        alt="Navigation screenshot" 
                      />
                    )}
                </div>
                <h4>Recommendations:</h4>
                <p>Reduce number of menu items for better clarity</p>
                <span className="complexity-tag easy">Easy</span>
                <p>Implement mega-menu for complex navigation</p>
                <span className="complexity-tag hard">Hard</span>
            </div>
            
            <div className="improvement-section">
                <h3>Main Content Area</h3>
                <div className="screenshot-container">
                    {results.site_data.main_screenshot && (
                      <img 
                        className="screenshot" 
                        src={`data:image/png;base64,${results.site_data.main_screenshot}`} 
                        alt="Main content screenshot" 
                      />
                    )}
                </div>
                <h4>Recommendations:</h4>
                <p>Improve content hierarchy with better headings</p>
                <span className="complexity-tag easy">Easy</span>
                <p>Optimize image loading speeds</p>
                <span className="complexity-tag medium">Medium</span>
            </div>
            
            <div className="improvement-section">
                <h3>Footer Section</h3>
                <div className="screenshot-container">
                    {results.site_data.footer_screenshot && (
                      <img 
                        className="screenshot" 
                        src={`data:image/png;base64,${results.site_data.footer_screenshot}`} 
                        alt="Footer screenshot" 
                      />
                    )}
                </div>
                <h4>Recommendations:</h4>
                <p>Add social media links and contact information</p>
                <span className="complexity-tag easy">Easy</span>
                <p>Implement footer search functionality</p>
                <span className="complexity-tag hard">Hard</span>
            </div>
            
            <div className="recommendations">
              <h2>Actionable Summary</h2>
              <div className="content">
                <ReactMarkdown>{results.summary}</ReactMarkdown>
              </div>
            </div>

            <div className="recommendations">
              <h2>Detailed Analysis</h2>
              <div className="content">
                <ReactMarkdown>{results.analysis}</ReactMarkdown>
              </div>
            </div>
          </div>

          {/* Print and Download Buttons */}
          <div className="action-buttons">
            <button onClick={handleDownloadPDF} className="download-btn">
              Download PDF
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;