/**
 * Base API configuration and utility functions
 * 
 * This module provides the core API setup, including:
 * - Base URL configuration
 * - Request/response handling
 * - Error processing
 * - Authentication handling
 */

// Base API URL - configurable for different environments
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

/**
 * Enhanced fetch function with error handling and response processing
 * 
 * @param {string} endpoint - API endpoint path (without base URL)
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<any>} - Promise resolving to the parsed API response
 * @throws {Error} - Throws detailed error on request failure
 */
export const fetchApi = async (endpoint, options = {}) => {
  // Prepare request URL
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  
  // Set default headers
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  // Process request body if present
  const config = {
    ...options,
    headers,
  };
  
  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body);
  }
  
  try {
    // Execute fetch request
    const response = await fetch(url, config);
    
    // Handle HTTP error responses
    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        // If response isn't valid JSON, use status text
        errorData = { error: response.statusText };
      }
      
      // Create detailed error object
      const error = new Error(errorData.error || 'API request failed');
      error.status = response.status;
      error.statusText = response.statusText;
      error.data = errorData;
      throw error;
    }
    
    // Check for empty response (e.g., 204 No Content)
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return null;
    }
    
    // Parse response as JSON
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    // Return raw response for non-JSON content
    return await response.text();
  } catch (error) {
    // Add request details to error
    error.endpoint = endpoint;
    error.request = { url, ...config };
    
    // Re-throw enhanced error
    throw error;
  }
};

/**
 * HTTP method wrappers for common API operations
 */

/**
 * GET request wrapper
 * 
 * @param {string} endpoint - API endpoint
 * @param {Object} options - Additional fetch options
 * @returns {Promise<any>} - API response
 */
export const get = (endpoint, options = {}) => {
  return fetchApi(endpoint, { 
    ...options, 
    method: 'GET' 
  });
};

/**
 * POST request wrapper
 * 
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request payload
 * @param {Object} options - Additional fetch options
 * @returns {Promise<any>} - API response
 */
export const post = (endpoint, data, options = {}) => {
  return fetchApi(endpoint, { 
    ...options, 
    method: 'POST', 
    body: data 
  });
};

/**
 * PUT request wrapper
 * 
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request payload
 * @param {Object} options - Additional fetch options
 * @returns {Promise<any>} - API response
 */
export const put = (endpoint, data, options = {}) => {
  return fetchApi(endpoint, { 
    ...options, 
    method: 'PUT', 
    body: data 
  });
};

/**
 * PATCH request wrapper
 * 
 * @param {string} endpoint - API endpoint
 * @param {Object} data - Request payload
 * @param {Object} options - Additional fetch options
 * @returns {Promise<any>} - API response
 */
export const patch = (endpoint, data, options = {}) => {
  return fetchApi(endpoint, { 
    ...options, 
    method: 'PATCH', 
    body: data 
  });
};

/**
 * DELETE request wrapper
 * 
 * @param {string} endpoint - API endpoint
 * @param {Object} options - Additional fetch options
 * @returns {Promise<any>} - API response
 */
export const del = (endpoint, options = {}) => {
  return fetchApi(endpoint, { 
    ...options, 
    method: 'DELETE' 
  });
};

export default {
  get,
  post,
  put,
  patch,
  del,
  fetchApi,
};