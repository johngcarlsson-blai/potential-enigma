import dash
from dash import dcc, html, dash_table, Input, Output, State, callback
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import io
import base64
import json
import os
import networkx as nx
import numpy as np
from contextlib import redirect_stdout, redirect_stderr
from network_graphs import EnhancedNetworkSwitcher, graphs
import os
import openai

# Configure Plotly to not auto-display (prevents terminal HTML output)
pio.renderers.default = None

# Configure OpenAI (you'll need to set your API key as an environment variable)
# Set OPENAI_API_KEY=your_key_here in your environment

# --- Branding ---
COMPANY_NAME = "BluelightAI"
PRODUCT_NAME = "Cobalt"
DASHBOARD_TITLE = f"{PRODUCT_NAME}: SAE Interpretability Dashboard by {COMPANY_NAME}"

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # This exposes the Flask server for deployment
app.title = DASHBOARD_TITLE

# Define the app layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1(f"{PRODUCT_NAME}: SAE Interpretability Dashboard", 
                style={'color': 'white', 'margin': 0, 'fontSize': '2.5rem', 'fontWeight': 'bold'}),
        html.P(f"by {COMPANY_NAME}", 
               style={'color': 'rgba(255,255,255,0.9)', 'margin': 0, 'fontSize': '1.2rem', 'fontWeight': '300'})
    ], style={
        'textAlign': 'center', 
        'padding': '25px',
        'background': 'linear-gradient(135deg, #1a365d 0%, #2d5a87 25%, #4299e1 50%, #667eea 75%, #764ba2 100%)',
        'color': 'white',
        'marginBottom': '30px',
        'boxShadow': '0 4px 15px rgba(0,0,0,0.2)'
    }),
    
    # Pie Charts Section (Hidden initially)
    html.Div(id='pie-charts-section', children=[], style={'display': 'none'}),
    
    # Chat Section (Hidden initially, shown after data upload)
    html.Div(id='chat-section', children=[], style={'display': 'none'}),
    
    # Data Grid Section (Hidden initially)
    html.Div(id='data-grid-section', children=[], style={'display': 'none'}),
    
    # File Upload Section (Always visible with working upload)
        # File Upload Section (Always visible with working upload)
    html.Div([
        html.H3("Upload Data", style={'color': '#1a365d', 'marginBottom': '15px', 'fontWeight': 'bold'}),
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                html.I(className='fas fa-upload', style={'fontSize': '2rem', 'marginBottom': '10px', 'color': '#4299e1'}),
                html.Br(),
                'Drag and Drop or ',
                html.A('Select Files', style={'color': '#2d5a87', 'textDecoration': 'underline', 'fontWeight': 'bold'}),
                html.Br(),
                html.Small('CSV Data File + JSON Config (optional)', style={'color': '#718096', 'fontSize': '0.9em'})
            ]),
            style={
                'width': '100%',
                'height': '120px',
                'lineHeight': '120px',
                'borderWidth': '2px',
                'borderStyle': 'dashed',
                'borderRadius': '10px',
                'textAlign': 'center',
                'margin': '10px',
                'borderColor': '#4299e1',
                'backgroundColor': '#f7fafc',
                'cursor': 'pointer',
                'transition': 'all 0.3s ease'
            },
            multiple=True  # Allow multiple files
        ),
        html.Div(id='upload-status', children=[], style={'textAlign': 'center', 'marginTop': '10px'})
    ], id='upload-section', style={'margin': '20px', 'padding': '20px', 'backgroundColor': '#edf2f7', 'borderRadius': '10px', 'border': '1px solid #cbd5e0'}),
    
    # Report Section (Hidden initially)
    html.Div(id='report-section', children=[], style={'display': 'none'}),
    
    # Knowledge Graph Section (Hidden initially)
    html.Div(id='knowledge-graph-section', children=[], style={'display': 'none'}),
    
    # Store for data
    dcc.Store(id='stored-data'),
    
    # Store for JSON reports
    dcc.Store(id='stored-reports'),
    
    # Store for chat history
    dcc.Store(id='chat-history', data=[])
    
], style={'fontFamily': 'Arial, sans-serif', 'margin': 0, 'padding': 0, 'backgroundColor': '#f7fafc', 'minHeight': '100vh'})

# Callback to handle file upload and process data
@app.callback(
    [Output('stored-data', 'data'),
     Output('stored-reports', 'data'),
     Output('pie-charts-section', 'children'),
     Output('pie-charts-section', 'style'),
     Output('chat-section', 'children'),
     Output('chat-section', 'style'),
     Output('data-grid-section', 'children'),
     Output('data-grid-section', 'style'),
     Output('upload-status', 'children'),
     Output('upload-section', 'style')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_dashboard(contents, filenames):
    if contents is None:
        return None, {}, [], {'display': 'none'}, [], {'display': 'none'}, [], {'display': 'none'}, [], {'margin': '20px', 'padding': '20px', 'backgroundColor': '#edf2f7', 'borderRadius': '10px', 'border': '1px solid #cbd5e0'}
    
    try:
        # Handle both single file and multiple files
        if not isinstance(contents, list):
            contents = [contents]
            filenames = [filenames]
        
        df = None
        json_data = None
        csv_filename = None
        json_filename = None
        
        # Process each uploaded file
        for content, filename in zip(contents, filenames):
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)
            
            if filename.lower().endswith('.csv'):
                # Process CSV file
                df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
                csv_filename = filename
                print(f"Successfully loaded CSV: {filename}")
                
            elif filename.lower().endswith('.json'):
                # Process JSON file
                try:
                    json_data = json.loads(decoded.decode('utf-8'))
                    json_filename = filename
                    print(f"Successfully loaded JSON: {filename}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON file {filename}: {e}")
        
        # Ensure we have at least a CSV file
        if df is None:
            raise ValueError("No valid CSV file found. Please upload a CSV file.")
        
        # Create pie charts (using JSON data if available)
        pie_charts = create_pie_charts(json_data)
        
        # Create chat section
        chat_section = create_chat_section()
        
        # Create data grid
        data_grid = create_data_grid(df)
        
        # Store JSON data for reports
        json_reports = json_data.get('reports', {}) if json_data else {}
        
        # Success status
        file_status = f"{csv_filename} ({len(df)} rows, {len(df.columns)} columns)"
        if json_filename:
            file_status += f" + {json_filename}"
        else:
            file_status += " (using default charts)"
            
        status_message = html.Div([
            html.I(className='fas fa-check-circle', style={'color': '#2ecc71', 'marginRight': '8px'}),
            f"✓ Successfully loaded: {file_status}"
        ], style={'color': '#1a365d', 'fontWeight': 'bold', 'fontSize': '14px'})
        
        upload_style_bottom = {
            'margin': '20px', 
            'padding': '15px', 
            'backgroundColor': '#f7fafc', 
            'borderRadius': '8px', 
            'border': '1px solid #e2e8f0',
            'marginTop': '40px'
        }
        
        return df.to_dict('records'), json_reports, pie_charts, {'display': 'block'}, chat_section, {'display': 'block'}, data_grid, {'display': 'block'}, status_message, upload_style_bottom
        
    except Exception as e:
        # Error status
        error_message = html.Div([
            html.I(className='fas fa-exclamation-triangle', style={'color': '#e74c3c', 'marginRight': '8px'}),
            f"Error: {str(e)}"
        ], style={'color': '#e74c3c', 'fontWeight': 'bold', 'fontSize': '14px'})
        
        return None, {}, [html.Div(f"Error processing file: {str(e)}", 
                              style={'color': 'red', 'textAlign': 'center'})], {'display': 'block'}, [], {'display': 'none'}, [], {'display': 'none'}, error_message, {'margin': '20px', 'padding': '20px', 'backgroundColor': '#edf2f7', 'borderRadius': '10px', 'border': '1px solid #cbd5e0'}


def create_pie_charts(json_data=None):
    """Create square tiles with large percentages from JSON data or use defaults"""
    
    if json_data and 'charts' in json_data:
        # Use data from JSON file
        chart_data = json_data['charts'][:3]  # Limit to 3 charts
        print(f"Using JSON data for {len(chart_data)} charts")
        # Get correlated SAE features from reports if available
        reports = json_data.get('reports', {})
    else:
        # Default sample data for tiles
        chart_data = [
            {'title': 'Model Attention Patterns', 'values': [30, 25, 20, 25]},
            {'title': 'Sentiment Distribution', 'values': [45, 35, 20]},
            {'title': 'Layer Activations', 'values': [40, 35, 25]}
        ]
        reports = {}
    
    tiles = []
    for i, data in enumerate(chart_data):
        if i >= 3:  # Only show 3 tiles
            break
            
        # Get the first value as percentage
        percentage = data['values'][0] if data.get('values') else 0
        
        # Get correlated SAE features for this chart
        correlated_features = []
        if str(i) in reports and 'correlated_sae_features' in reports[str(i)]:
            correlated_features = reports[str(i)]['correlated_sae_features']
        
        # Create features display
        features_display = html.Div([
            html.P("Correlated SAE Features:", 
                   style={'margin': '0', 'fontSize': '11px', 'color': '#1a365d', 'fontWeight': 'bold'}),
            html.P(f"[{', '.join(map(str, correlated_features))}]" if correlated_features else "No features available",
                   style={'margin': '2px 0 0 0', 'fontSize': '10px', 'color': '#4a5568', 'fontFamily': 'monospace'})
        ]) if correlated_features else html.Div()
        
        tile = html.Div([
            # Large percentage number (CLICKABLE for reports)
            html.Button(f"{percentage}%", 
                       id=f'percentage-btn-{i}',  # Different ID for percentage clicks
                       style={
                           'fontSize': '3.5rem',
                           'fontWeight': 'bold',
                           'color': '#1a365d',
                           'backgroundColor': 'transparent',
                           'border': 'none',
                           'cursor': 'pointer',
                           'textAlign': 'center',
                           'marginBottom': '10px',
                           'lineHeight': '1',
                           'padding': '0',
                           'transition': 'all 0.3s ease',
                           'width': '100%'
                       }),
            
            # Title
            html.Div(data['title'], 
                     style={
                         'fontSize': '14px',
                         'fontWeight': 'bold',
                         'color': '#2d5a87',
                         'textAlign': 'center',
                         'marginBottom': '15px',
                         'lineHeight': '1.2'
                     }),
            
            # Correlated SAE Features
            features_display,
            
            # SAE Knowledge Graph Button
            html.Div([
                html.Button('SAE Knowledge Graph', 
                           id=f'graph-btn-{i}',
                           style={
                               'backgroundColor': '#2d5a87',
                               'color': 'white',
                               'border': 'none',
                               'padding': '8px 16px',
                               'borderRadius': '6px',
                               'cursor': 'pointer',
                               'fontSize': '12px',
                               'fontWeight': 'bold',
                               'width': '100%',
                               'transition': 'all 0.3s ease',
                               'boxShadow': '0 2px 4px rgba(0,0,0,0.2)'
                           })
            ], style={'marginTop': '15px'})
            
        ], style={
            'width': '15%',  # 3 tiles instead of 4
            'display': 'inline-block',
            'margin': '1%',
            'padding': '25px',
            'backgroundColor': '#ffffff',
            'borderRadius': '12px',
            'boxShadow': '0 4px 12px rgba(0,0,0,0.1)',
            'border': '2px solid #e2e8f0',
            'textAlign': 'center',
            'minHeight': '240px',
            'transition': 'all 0.3s ease',
            'position': 'relative'
        })
        
        tiles.append(tile)
    
    return [
        html.H3("SAE Feature Analysis", 
                style={
                    'color': '#1a365d', 
                    'textAlign': 'center', 
                    'marginBottom': '30px', 
                    'fontWeight': 'bold', 
                    'fontSize': '2rem'
                }),
        html.Div(tiles, style={'textAlign': 'center', 'marginBottom': '20px'})
    ]

def create_chat_section():
    """Create chat interface for asking questions about the data"""
    return [
        html.Div([
            html.H3("Ask Questions About Your Data", 
                    style={
                        'color': '#1a365d', 
                        'textAlign': 'center', 
                        'marginBottom': '20px', 
                        'fontWeight': 'bold', 
                        'fontSize': '1.8rem'
                    }),
            
            # Chat messages area
            html.Div(id='chat-messages', 
                    children=[], 
                    style={
                        'minHeight': '300px',
                        'maxHeight': '500px', 
                        'overflowY': 'auto',
                        'backgroundColor': '#ffffff',
                        'border': '1px solid #e2e8f0',
                        'borderRadius': '10px',
                        'padding': '15px',
                        'marginBottom': '15px',
                        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                    }),
            
            # Chat input area
            html.Div([
                dcc.Input(
                    id='chat-input',
                    type='text',
                    placeholder='Ask about the data... e.g. "What are the biggest causes of failure?"',
                    autoComplete='off',
                    style={
                        'width': '80%',
                        'padding': '12px',
                        'border': '1px solid #cbd5e0',
                        'borderRadius': '6px',
                        'fontSize': '14px',
                        'marginRight': '10px',
                        'outline': 'none'
                    }
                ),
                html.Button('Send', 
                           id='chat-send',
                           style={
                               'width': '18%',
                               'padding': '12px',
                               'backgroundColor': '#2d5a87',
                               'color': 'white',
                               'border': 'none',
                               'borderRadius': '6px',
                               'cursor': 'pointer',
                               'fontSize': '14px',
                               'fontWeight': 'bold',
                               'transition': 'all 0.3s ease'
                           })
            ], style={'display': 'flex', 'alignItems': 'center'})
            
        ], style={
            'margin': '20px', 
            'padding': '25px', 
            'backgroundColor': '#f7fafc', 
            'borderRadius': '12px', 
            'border': '1px solid #e2e8f0',
            'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'
        })
    ]

def create_data_grid(df):
    """Create data grid from uploaded DataFrame"""
    
    # Create simple columns without any style properties
    columns = [{"name": col, "id": col, "type": "text"} for col in df.columns]
    
    # Create conditional styling for alternating rows
    style_data_conditional = [
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': '#f7fafc'
        },
        {
            'if': {'row_index': 'even'},
            'backgroundColor': '#ffffff'
        }
    ]
    
    # Create cell-specific width styling using style_cell_conditional
    style_cell_conditional = []
    for col in df.columns:
        if col.lower() in ['id', 'index', 'row']:
            # Very narrow for simple IDs/indexes
            style_cell_conditional.append({
                'if': {'column_id': col},
                'width': '50px',
                'maxWidth': '50px'
            })
        elif len(col) <= 2 or (len(df) > 0 and df[col].astype(str).str.len().max() <= 2):
            # Single character or very short content - minimal width
            style_cell_conditional.append({
                'if': {'column_id': col},
                'width': '40px',
                'maxWidth': '40px'
            })
        elif col.lower() in ['timestamp', 'date', 'time']:
            style_cell_conditional.append({
                'if': {'column_id': col},
                'width': '100px',
                'maxWidth': '100px'
            })
        elif any(word in col.lower() for word in ['description', 'content', 'text', 'comment', 'note']):
            style_cell_conditional.append({
                'if': {'column_id': col},
                'width': '150px',
                'maxWidth': '150px'
            })
        else:
            # Default reasonable width
            style_cell_conditional.append({
                'if': {'column_id': col},
                'width': '80px',
                'maxWidth': '80px'
            })
    
    return [
        html.H3("Data Overview", style={'color': '#1a365d', 'marginTop': '30px', 'marginBottom': '15px', 'fontWeight': 'bold', 'fontSize': '1.8rem'}),
        html.Div([
            dash_table.DataTable(
                id='data-table',
                data=df.to_dict('records'),
                columns=columns,
                page_size=15,
                style_table={
                    'overflowX': 'auto',
                    'border': '1px solid #cbd5e0',
                    'maxHeight': '400px',
                    'overflowY': 'auto'
                },
                style_header={
                    'backgroundColor': '#1a365d',
                    'color': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'padding': '8px',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '12px',
                    'whiteSpace': 'nowrap',
                    'textOverflow': 'ellipsis',
                    'overflow': 'hidden'
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '6px',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '12px',
                    'border': '1px solid #e2e8f0',
                    'color': '#2d3748',
                    'whiteSpace': 'nowrap',
                    'textOverflow': 'ellipsis',
                    'overflow': 'hidden'
                },
                style_data_conditional=style_data_conditional,
                style_cell_conditional=style_cell_conditional,
                sort_action="native",
                filter_action="native",
                tooltip_data=[
                    {
                        column: {'value': str(value), 'type': 'markdown'}
                        for column, value in row.items()
                    } for row in df.to_dict('records')
                ],
                tooltip_duration=None
            )
        ], style={'margin': '20px', 'padding': '20px', 'backgroundColor': '#ffffff', 'borderRadius': '10px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'border': '1px solid #e2e8f0'})
    ]

def create_knowledge_graph(chart_index=None, json_reports=None, button_clicked=None):
    """
    Create enhanced NetworkX visualization using the sophisticated graphs from network_graphs.py
    Returns a clean Plotly figure for use in Dash modal without any terminal output
    Always shows all 12 sophisticated graphs in 3D view regardless of which button was clicked
    """
    # Suppress any potential output completely
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        try:
            # Create the enhanced network switcher with your sophisticated graphs
            switcher = EnhancedNetworkSwitcher(graphs)
            
            # Always get all graphs in 3D view (not a single graph)
            # This shows all 12 sophisticated graphs from network_graphs.py
            # Pass json_reports and button_clicked to handle correlated SAE features
            fig = switcher.get_3d_figure(single_graph_index=None, json_reports=json_reports, button_clicked=button_clicked)
            
            # Use a general title since all buttons show the same thing
            fig.update_layout(
                title={
                    'text': 'SAE Knowledge Graphs - All 12 Networks (Use dropdown to view individual graphs)',
                    'x': 0.5,
                    'font': {'size': 14, 'color': '#1a365d'}
                }
            )
            
            return fig
            
        except Exception as e:
            # Fallback: create a simple default graph if the sophisticated graphs fail
            fig = go.Figure()
            fig.add_trace(go.Scatter3d(
                x=[0, 1, 0.5], 
                y=[0, 0, 0.8], 
                z=[0, 0, 0.5],
                mode='markers+lines',
                marker=dict(size=8, color='#4299e1'),
                line=dict(color='#2d5a87', width=2),
                text=['Node A', 'Node B', 'Node C'],
                hovertemplate='SAE Feature %{text}<extra></extra>'
            ))
            
            fig.update_layout(
                title={'text': f'SAE Knowledge Graph {chart_index+1}', 'x': 0.5},
                scene=dict(
                    xaxis=dict(showbackground=False, showticklabels=False, title=""),
                    yaxis=dict(showbackground=False, showticklabels=False, title=""),
                    zaxis=dict(showbackground=False, showticklabels=False, title="")
                ),
                margin=dict(l=0, r=0, b=0, t=40),
                height=400,
                width=500
            )
            
            return fig

# Callback to handle knowledge graph button clicks
@app.callback(
    [Output('knowledge-graph-section', 'children'),
     Output('knowledge-graph-section', 'style')],
    [Input('graph-btn-0', 'n_clicks'),
     Input('graph-btn-1', 'n_clicks'),
     Input('graph-btn-2', 'n_clicks')],
    [State('stored-reports', 'data')]
)
def display_knowledge_graph(btn0, btn1, btn2, stored_reports):
    if not any([btn0, btn1, btn2]):
        return [], {'display': 'none'}
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return [], {'display': 'none'}
    
    # Determine which button was clicked
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    chart_num = int(button_id.split('-')[-1])
    
    # Create knowledge graph (always shows all graphs now) with JSON reports and button info
    fig = create_knowledge_graph(json_reports=stored_reports, button_clicked=chart_num)
    
    graph_content = [
        # Store which button was clicked for the modal
        html.Div(id='stored-button-clicked', children=str(chart_num), style={'display': 'none'}),
        html.Div([
            html.H3('SAE Knowledge Graphs - All Networks', 
                   style={'color': '#1a365d', 'marginBottom': '15px', 'fontWeight': 'bold', 'textAlign': 'center'}),
            
            # Dropdown for selecting view
            html.Div([
                html.Label('View:', style={'marginRight': '10px', 'fontWeight': 'bold', 'color': '#1a365d'}),
                dcc.Dropdown(
                    id='graph-view-dropdown',
                    options=[
                        {'label': '3D View - All 12 Networks', 'value': 'all'},
                        {'label': 'Layer 1', 'value': 0},
                        {'label': 'Layer 2', 'value': 1},
                        {'label': 'Layer 3', 'value': 2},
                        {'label': 'Layer 4', 'value': 3},
                        {'label': 'Layer 5', 'value': 4},
                        {'label': 'Layer 6', 'value': 5},
                        {'label': 'Layer 7', 'value': 6},
                        {'label': 'Layer 8', 'value': 7},
                        {'label': 'Layer 9', 'value': 8},
                        {'label': 'Layer 10', 'value': 9},
                        {'label': 'Layer 11', 'value': 10},
                        {'label': 'Layer 12', 'value': 11}
                    ],
                    value='all',
                    style={'width': '300px'}
                )
            ], style={'textAlign': 'center', 'marginBottom': '15px'}),
            
            # Graph display area
            dcc.Graph(id='knowledge-graph-display', figure=fig, config={'displayModeBar': True}),
            
            html.Div([
                html.Button('Close Graph', id='close-graph', 
                           style={
                               'backgroundColor': '#1a365d',
                               'color': 'white',
                               'border': 'none',
                               'padding': '10px 20px',
                               'borderRadius': '6px',
                               'cursor': 'pointer',
                               'fontSize': '12px',
                               'fontWeight': 'bold',
                               'marginTop': '15px'
                           })
            ], style={'textAlign': 'center'})
        ], style={
            'position': 'fixed',
            'top': '50%',
            'left': '50%',
            'transform': 'translate(-50%, -50%)',
            'width': '900px',  # Made wider to accommodate larger graph
            'height': '80vh',  # Made taller
            'backgroundColor': '#ffffff',
            'padding': '20px',
            'borderRadius': '12px',
            'boxShadow': '0 15px 40px rgba(26, 54, 93, 0.3)',
            'zIndex': '1001',
            'border': '2px solid #4299e1',
            'overflow': 'auto'  # Allow scrolling if needed
        }),
        # Background overlay
        html.Div(style={
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'width': '100%',
            'height': '100%',
            'backgroundColor': 'rgba(0,0,0,0.5)',
            'zIndex': '1000'
        })
    ]
    
    return graph_content, {'display': 'block'}

# Callback to close the knowledge graph
@app.callback(
    [Output('knowledge-graph-section', 'children', allow_duplicate=True),
     Output('knowledge-graph-section', 'style', allow_duplicate=True)],
    [Input('close-graph', 'n_clicks')],
    prevent_initial_call=True
)
def close_knowledge_graph(n_clicks):
    if n_clicks:
        return [], {'display': 'none'}
    return dash.no_update, dash.no_update

# Callback to handle dropdown selection in the knowledge graph modal
@app.callback(
    Output('knowledge-graph-display', 'figure'),
    [Input('graph-view-dropdown', 'value')],
    [State('stored-reports', 'data'),
     State('stored-button-clicked', 'children')],
    prevent_initial_call=True
)
def update_graph_display(selected_view, stored_reports, button_clicked_str):
    """Update the graph display based on dropdown selection"""
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        try:
            switcher = EnhancedNetworkSwitcher(graphs)
            
            # Convert button_clicked back to int
            button_clicked = int(button_clicked_str) if button_clicked_str else 0
            
            if selected_view == 'all':
                # Show all graphs in 3D view
                fig = switcher.get_3d_figure(single_graph_index=None, json_reports=stored_reports, button_clicked=button_clicked)
                fig.update_layout(
                    title={
                        'text': 'SAE Knowledge Graphs - All 12 Networks',
                        'x': 0.5,
                        'font': {'size': 16, 'color': '#1a365d'}
                    },
                    width=850,
                    height=600
                )
            else:
                # Show individual graph
                graph_index = int(selected_view)
                fig = switcher.get_3d_figure(single_graph_index=graph_index, json_reports=stored_reports, button_clicked=button_clicked)
                
                fig.update_layout(
                    title={
                        'text': f'SAE Knowledge Graph - Layer {graph_index+1} (150 nodes)',
                        'x': 0.5,
                        'font': {'size': 16, 'color': '#1a365d'}
                    },
                    width=850,
                    height=600
                )
            
            return fig
            
        except Exception as e:
            # Fallback figure
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading graph: {str(e)}",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16, color='red')
            )
            fig.update_layout(
                width=850,
                height=600,
                title="Error Loading Graph"
            )
            return fig

# Callback to handle pie chart clicks and show reports
# Replace the existing report callback (around line 599) with this:
@app.callback(
    [Output('report-section', 'children'),
     Output('report-section', 'style')],
    [Input('percentage-btn-0', 'n_clicks'),
     Input('percentage-btn-1', 'n_clicks'),
     Input('percentage-btn-2', 'n_clicks')],  # Now listening to percentage button clicks
    [State('stored-reports', 'data')]
)
def display_report(btn0, btn1, btn2, stored_reports):
    if not any([btn0, btn1, btn2]):
        return [], {'display': 'none'}
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return [], {'display': 'none'}
    
    # Determine which percentage button was clicked
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    chart_num = button_id.split('-')[-1]  # Extract chart number from percentage-btn-X
    
    # Use stored reports from JSON if available, otherwise use defaults
    if stored_reports and chart_num in stored_reports:
        report = stored_reports[chart_num]
    else:
        # Default/fallback reports
        default_reports = {
            '0': {
                'title': 'Negative Constraint Processing Analysis',
                'content': """**Executive Summary:**
Our analysis reveals a systematic issue where AI image generation models consistently include forbidden objects when users specify what they *don't* want in their images. When users request "a kitchen with no elephants" or "a living room without tigers," the model paradoxically generates images containing exactly these unwanted elements.

**Key Findings:**
- 73% of negative constraint prompts result in the forbidden object appearing
- The issue is most pronounced with animal-related constraints (85% failure rate)
- Simple negations like "no red" perform better than complex object negations (45% failure rate)

**Technical Analysis:**
The problem stems from how the model processes negation in natural language. When the prompt contains "no elephants," the model's attention mechanism actually increases focus on elephant-related features rather than avoiding them.

**Recommendations:**
- Implement attention masking for negated concepts
- Use positive framing ("show only kitchen items")
- Deploy specialized negation handling in prompt preprocessing""",
                'correlated_sae_features': [9361, 10285, 15020]
            },
            '1': {
                'title': 'Size Comparison Processing Report',
                'content': """**Executive Summary:**
Analysis of how AI models handle relative size comparisons reveals significant inconsistencies in spatial reasoning and scale understanding.

**Key Findings:**
- Models struggle with abstract size relationships (62% accuracy)
- Physical object comparisons perform better (78% accuracy)  
- Multi-object size hierarchies often collapse (43% accuracy)

**Technical Details:**
The model shows bias toward learned size associations rather than contextual reasoning. For example, "tiny elephant" often produces normal-sized elephants, while "giant mouse" may produce mouse-sized results.

**Mitigation Strategies:**
- Implement scale-aware attention mechanisms
- Use comparative training data with explicit size relationships
- Deploy multi-modal size verification systems""",
                'correlated_sae_features': [10552, 7740, 23473]
            },
            '2': {
                'title': 'Large Crowds Report',
                'content': """**Executive Summary:**
Investigation into AI model performance on crowd scenes and group dynamics reveals both strengths and significant limitations.

**Key Findings:**
- Crowd density estimation accuracy: 67%
- Individual face recognition in crowds: 34% accuracy
- Crowd behavior prediction: 45% accuracy

**Technical Challenges:**
- Occlusion handling remains problematic
- Scale variation across crowd depth poorly managed
- Motion blur in dynamic crowd scenes degrades performance

**Recommended Improvements:**
- Implement hierarchical crowd analysis frameworks
- Deploy multi-scale feature extraction
- Use temporal consistency constraints for crowd tracking""",
                'correlated_sae_features': [10552, 7740, 23473]
            }
        }
        report = default_reports.get(chart_num, default_reports['0'])
    
    # Create the report modal
    report_content = [
        html.Div([
            html.Div([
                html.Button('×', id='close-report', 
                           style={
                               'position': 'absolute',
                               'top': '15px',
                               'right': '20px',
                               'backgroundColor': 'transparent',
                               'border': 'none',
                               'fontSize': '24px',
                               'cursor': 'pointer',
                               'color': '#718096',
                               'fontWeight': 'bold'
                           })
            ]),
            html.H2(report['title'], 
                   style={
                       'color': '#1a365d', 
                       'marginBottom': '25px', 
                       'fontWeight': 'bold', 
                       'fontSize': '1.8rem',
                       'borderBottom': '2px solid #4299e1',
                       'paddingBottom': '10px'
                   }),
            html.Div([
                dcc.Markdown(report['content'], 
                           style={
                               'lineHeight': '1.7',
                               'fontSize': '15px',
                               'color': '#2d3748'
                           })
            ], style={
                'backgroundColor': '#f7fafc',
                'padding': '25px',
                'borderRadius': '10px',
                'border': '1px solid #e2e8f0',
                'marginBottom': '20px'
            }),
            
            # Show correlated SAE features if available
            html.Div([
                html.H4("Correlated SAE Features:", 
                       style={'color': '#1a365d', 'marginBottom': '10px', 'fontSize': '16px'}),
                html.P(f"Features: {report.get('correlated_sae_features', 'None available')}", 
                      style={
                          'fontFamily': 'monospace',
                          'backgroundColor': '#edf2f7',
                          'padding': '10px',
                          'borderRadius': '5px',
                          'fontSize': '14px',
                          'color': '#2d5a87'
                      })
            ], style={'marginBottom': '25px'}) if 'correlated_sae_features' in report else html.Div(),
            
            html.Div([
                html.Button('Close Report', id='close-report-main', 
                           style={
                               'backgroundColor': '#1a365d',
                               'color': 'white',
                               'border': 'none',
                               'padding': '12px 24px',
                               'borderRadius': '8px',
                               'cursor': 'pointer',
                               'fontSize': '14px',
                               'fontWeight': 'bold',
                               'transition': 'all 0.3s ease',
                               'boxShadow': '0 2px 4px rgba(0,0,0,0.2)'
                           })
            ], style={'textAlign': 'center'})
        ], style={
            'position': 'fixed',
            'top': '50%',
            'left': '50%',
            'transform': 'translate(-50%, -50%)',
            'width': '85%',
            'maxWidth': '900px',
            'maxHeight': '85vh',
            'overflowY': 'auto',
            'backgroundColor': '#ffffff',
            'padding': '30px',
            'borderRadius': '15px',
            'boxShadow': '0 20px 60px rgba(26, 54, 93, 0.3)',
            'zIndex': '99999',
            'border': '2px solid #4299e1'
        }),
        # Background overlay
        html.Div(style={
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'width': '100%',
            'height': '100%',
            'backgroundColor': 'rgba(0,0,0,0.6)',
            'zIndex': '99998'
        })
    ]
    
    return report_content, {'display': 'block'}

# Update the close report callback to handle both close buttons
@app.callback(
    [Output('report-section', 'children', allow_duplicate=True),
     Output('report-section', 'style', allow_duplicate=True)],
    [Input('close-report', 'n_clicks'),
     Input('close-report-main', 'n_clicks')],
    prevent_initial_call=True
)
def close_report(n_clicks1, n_clicks2):
    if n_clicks1 or n_clicks2:
        return [], {'display': 'none'}
    return dash.no_update, dash.no_update

# Chat callback to handle user questions (both button click and Enter key)
@app.callback(
    [Output('chat-messages', 'children'),
     Output('chat-input', 'value'),
     Output('chat-history', 'data')],
    [Input('chat-send', 'n_clicks'),
     Input('chat-input', 'n_submit')],
    [State('chat-input', 'value'),
     State('stored-reports', 'data'),
     State('stored-data', 'data'),
     State('chat-history', 'data')]
)
def handle_chat(n_clicks, n_submit, message, reports_data, csv_data, chat_history):
    if (not n_clicks and not n_submit) or not message or not message.strip():
        return chat_history if chat_history else [], '', chat_history if chat_history else []
    
    try:
        # Create context from the data for the AI
        context_parts = []
        
        # Send the complete JSON data for comprehensive analysis
        if reports_data:
            context_parts.append("COMPLETE DATA:")
            for key, report in reports_data.items():
                # Convert 0-indexed to 1-indexed for user-facing display
                display_key = str(int(key) + 1)
                context_parts.append(f"Analysis {display_key}: {report.get('title', 'Unknown')}")
                context_parts.append(f"Full content: {report.get('content', '')}")
                if 'correlated_sae_features' in report:
                    context_parts.append(f"Correlated SAE features: {report.get('correlated_sae_features', [])}")
        
        if csv_data:
            context_parts.append(f"CSV data contains {len(csv_data)} rows")
            if csv_data:
                columns = list(csv_data[0].keys()) if csv_data else []
                context_parts.append(f"CSV columns: {columns}")
        
        context = "\n".join(context_parts)
        
        # Call OpenAI API (safely handle if no API key)
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            answer = "⚠️ OpenAI API key not configured. Please set OPENAI_API_KEY environment variable to enable AI responses. For now, I can tell you that your data contains the reports and CSV information shown above."
        else:
            try:
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": """You are an AI assistant analyzing SAE (Sparse Autoencoder) interpretability data. 

CRITICAL INSTRUCTIONS:
- Never mention "reports" or "JSON files" - speak as if you have direct knowledge of the data
- When referencing different failure causes, use 1-indexed numbers (1, 2, 3) not 0-indexed
- Always format SAE feature numbers as clickable links using markdown format with target="_blank":
  [10285](https://openaipublic.blob.core.windows.net/sparse-autoencoder/sae-viewer/index.html#/model/gpt2-small/family/v5_32k/layer/8/location/resid_post_mlp/feature/10285)
- Include SAE feature references naturally in your explanations
- For multiple features, use commas AND SPACES to separate them and NEVER keep them in the same link!  That is wrong!
- Be helpful and focus on the data provided
- Sound natural and knowledgeable, as if this is your own analysis"""},
                        {"role": "user", "content": f"Based on this data context:\n{context}\n\nUser question: {message}"}
                    ],
                    max_tokens=1500,
                    temperature=0.7
                )
                answer = response.choices[0].message.content
            except Exception as e:
                answer = f"⚠️ Error calling OpenAI API: {str(e)}. Please check your API key and internet connection."
        
        # Add to chat history
        new_chat_entry = [
            html.Div([
                html.Strong("You: ", style={'color': '#2d5a87'}),
                html.Span(message, style={'color': '#2d3748'})
            ], style={'marginBottom': '10px', 'padding': '10px', 'backgroundColor': '#edf2f7', 'borderRadius': '8px'}),
            html.Div([
                html.Strong("AI: ", style={'color': '#1a365d'}),
                dcc.Markdown(answer, link_target="_blank", style={'color': '#2d3748', 'margin': '0'})
            ], style={'marginBottom': '15px', 'padding': '10px', 'backgroundColor': '#ffffff', 'borderRadius': '8px', 'border': '1px solid #e2e8f0'})
        ]
        
        updated_history = (chat_history if chat_history else []) + new_chat_entry
        
        return updated_history, '', updated_history
        
    except Exception as e:
        error_message = [
            html.Div([
                html.Strong("Error: ", style={'color': '#e74c3c'}),
                html.Span(f"Failed to process your question: {str(e)}", style={'color': '#2d3748'})
            ], style={'marginBottom': '10px', 'padding': '10px', 'backgroundColor': '#fed7d7', 'borderRadius': '8px'})
        ]
        
        updated_history = (chat_history if chat_history else []) + error_message
        return updated_history, '', updated_history

if __name__ == '__main__':
    if __name__ == '__main__':
        #app.run_server(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)), debug=False)
        app.run(debug=True, port=8050)
