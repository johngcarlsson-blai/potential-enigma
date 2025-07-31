import networkx as nx
import plotly.graph_objects as go
import plotly.colors as colors
import numpy as np
from IPython.display import display
import ipywidgets as widgets

# Create diverse, visually appealing graphs
graphs = []
num_graphs = 12
num_nodes_per_graph = 150

def create_structured_graph(graph_type, nodes, seed):
    """Create different types of structured graphs that look good"""
    np.random.seed(seed)
    
    if graph_type == "tree_plus":
        # Start with a random tree, then add some cycles
        # Create a random tree by generating a connected graph with n-1 edges
        G = nx.Graph()
        G.add_nodes_from(range(nodes))
        
        # Build tree by connecting each new node to a random existing node
        for i in range(1, nodes):
            existing_node = np.random.choice(i)
            G.add_edge(i, existing_node)
        
        # Add 3-5 random edges to create interesting cycles
        extra_edges = np.random.randint(3, 6)
        possible_edges = [(u, v) for u in range(nodes) for v in range(u+1, nodes) if not G.has_edge(u, v)]
        if possible_edges:
            new_edges = np.random.choice(len(possible_edges), min(extra_edges, len(possible_edges)), replace=False)
            for idx in new_edges:
                G.add_edge(*possible_edges[idx])
        return G
    
    elif graph_type == "small_world":
        # Small world networks look great - local clustering with some long-range connections
        k = 3  # Each node connected to 4 nearest neighbors
        p = 0.3  # Probability of rewiring
        return nx.watts_strogatz_graph(nodes, k, p, seed=seed)
    
    elif graph_type == "scale_free":
        # Scale-free networks have hubs - very realistic for many real networks
        m = 2  # Number of edges to attach from new node
        return nx.barabasi_albert_graph(nodes, m, seed=seed)
    
    elif graph_type == "community":
        # Create a graph with clear community structure
        # Make 3-4 communities
        community_sizes = [nodes//3, nodes//3, nodes - 2*(nodes//3)]
        p_in = 0.3   # High probability within communities
        p_out = 0.1  # Low probability between communities
        return nx.stochastic_block_model(community_sizes, [[p_in, p_out, p_out], 
                                                          [p_out, p_in, p_out],
                                                          [p_out, p_out, p_in]], seed=seed)
    
    elif graph_type == "grid_plus":
        # Start with a grid, then add some random connections
        side = int(np.sqrt(nodes))
        G = nx.grid_2d_graph(side, side)
        # Convert to integer labels
        G = nx.convert_node_labels_to_integers(G)
        # Add extra nodes if needed
        while G.number_of_nodes() < nodes:
            G.add_node(G.number_of_nodes())
        # Add some random long-range connections
        extra_edges = nodes // 4
        for _ in range(extra_edges):
            u, v = np.random.choice(nodes, 2, replace=False)
            if not G.has_edge(u, v):
                G.add_edge(u, v)
        return G
    
    elif graph_type == "circular_plus":
        # Circular layout with some internal connections
        G = nx.cycle_graph(nodes)
        # Add some chord edges across the circle
        for _ in range(nodes // 3):
            u, v = np.random.choice(nodes, 2, replace=False)
            if not G.has_edge(u, v):
                G.add_edge(u, v)
        return G
    
    elif graph_type == "hub_spoke":
        # Create hub-and-spoke pattern with multiple hubs
        G = nx.Graph()
        G.add_nodes_from(range(nodes))
        num_hubs = 3
        hubs = np.random.choice(nodes, num_hubs, replace=False)
        
        # Connect each non-hub node to 1-2 hubs
        for node in range(nodes):
            if node not in hubs:
                connected_hubs = np.random.choice(hubs, np.random.randint(1, 3), replace=False)
                for hub in connected_hubs:
                    G.add_edge(node, hub)
        
        # Add some connections between non-hub nodes
        non_hubs = [n for n in range(nodes) if n not in hubs]
        for _ in range(len(non_hubs) // 3):
            u, v = np.random.choice(non_hubs, 2, replace=False)
            if not G.has_edge(u, v):
                G.add_edge(u, v)
        return G
    
    else:  # "random_connected"
        # Better random graph - ensure it's connected and not too dense
        while True:
            G = nx.gnm_random_graph(nodes, nodes + 3, seed=seed)
            if nx.is_connected(G):
                return G

# Create 10 different graph types for variety
graph_types = ["tree_plus", "small_world", "scale_free", "community", "grid_plus", 
               "circular_plus", "hub_spoke", "tree_plus", "small_world", "scale_free","tree_plus","tree_plus"]

for i in range(num_graphs):
    graph_type = graph_types[i]
    graph = create_structured_graph(graph_type, num_nodes_per_graph, seed=i*10)
    graphs.append(graph)

class EnhancedNetworkSwitcher:
    def __init__(self, graphs):
        self.graphs = graphs
        self.num_graphs = len(graphs)
        
        # Pre-compute layouts
        self.layouts_2d = [nx.spring_layout(g, seed=42) for g in graphs]
        self.layouts_3d = self._compute_3d_layouts()
        
        # Use the same color scheme as your original code
        self.categorical_colors = colors.qualitative.Plotly[:self.num_graphs]
        
        # Create dropdown for switching
        self.dropdown = widgets.Dropdown(
            options=[('3D View - All Graphs', '3d')] + [(f'Graph {i+1} (2D)', i) for i in range(self.num_graphs)],
            value='3d',
            description='View:',
            style={'description_width': 'initial'}
        )
        
        # Create output widget to hold the figure
        self.output = widgets.Output()
        
        # Set up the dropdown callback
        self.dropdown.observe(self._on_dropdown_change, names='value')
        
        # Initialize with 3D view (but don't display to prevent terminal output)
        # self._show_3d()  # Commented out to prevent automatic display
        
    def _compute_3d_layouts(self):
        """Convert 2D layouts to 3D with your original spacing logic"""
        adjusted_layouts_3d = []
        x_spacing_factor = 1
        
        for i, layout in enumerate(self.layouts_2d):
            layout_3d = {}
            x_plane = (i + 1) * x_spacing_factor
            for node, pos in layout.items():
                # Create 3D position: (x_plane, y, z) where z is the original x
                layout_3d[node] = (x_plane, pos[1], pos[0])
            adjusted_layouts_3d.append(layout_3d)
        
        return adjusted_layouts_3d
    
    def _show_3d(self):
        """Create and display 3D view using your original code logic"""
        fig = go.Figure()
        
        # Your original 3D plotting logic
        for i, (graph, layout_3d) in enumerate(zip(self.graphs, self.layouts_3d)):
            # Add nodes
            node_x = []
            node_y = []
            node_z = []
            
            for node in graph.nodes():
                if node not in layout_3d:
                    continue
                x, y, z = layout_3d[node]
                node_x.append(x)
                node_y.append(y)
                node_z.append(z)

            node_trace = go.Scatter3d(
                x=node_x,
                y=node_y,
                z=node_z,
                mode='markers',
                marker=dict(
                    size=8,
                    color=self.categorical_colors[i % len(self.categorical_colors)]
                ),
                name=f'Layer {i+1}',
                hovertemplate=f'Layer {i+1}<br>Node: %{{text}}<extra></extra>',
                text=[str(node) for node in graph.nodes() if node in layout_3d]
            )
            fig.add_trace(node_trace)

            # Add edges
            edge_x = []
            edge_y = []
            edge_z = []
            for edge in graph.edges():
                if edge[0] not in layout_3d or edge[1] not in layout_3d:
                    continue
                x0, y0, z0 = layout_3d[edge[0]]
                x1, y1, z1 = layout_3d[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
                edge_z.extend([z0, z1, None])

            edge_trace = go.Scatter3d(
                x=edge_x,
                y=edge_y,
                z=edge_z,
                mode='lines',
                line=dict(
                    color='gray',
                    width=2
                ),
                hoverinfo='none',
                name=f'Graph {i+1} Edges',
                showlegend=False
            )
            fig.add_trace(edge_trace)

        # Your original layout settings
        fig.update_layout(
            title='Force-Directed Graphs in 3D Planes - Use dropdown to view individual graphs',
            scene=dict(
                xaxis=dict(title='X (Plane)'),
                yaxis=dict(title='Y'),
                zaxis=dict(title='Z'),
                aspectmode='manual',
                aspectratio=dict(x=3, y=1, z=1),
                camera=dict(
                    center=dict(x=0, y=0, z=0),
                    eye=dict(x=0.01, y=-2.5, z=0.01)
                )
            ),
            margin=dict(l=0, r=0, b=0, t=40),
            showlegend=True,
            width=900,
            height=700
        )
        
        # Clear output and show new figure
        with self.output:
            self.output.clear_output(wait=True)
            fig.show()
    
    def _show_2d(self, graph_idx):
        """Create and display 2D view of selected graph"""
        fig = go.Figure()
        
        graph = self.graphs[graph_idx]
        pos = self.layouts_2d[graph_idx]
        color = self.categorical_colors[graph_idx % len(self.categorical_colors)]
        
        # Add edges
        edge_x = []
        edge_y = []
        for edge in graph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            line=dict(width=2, color='gray'),
            hoverinfo='skip',
            showlegend=False
        ))
        
        # Add nodes
        node_x = [pos[node][0] for node in graph.nodes()]
        node_y = [pos[node][1] for node in graph.nodes()]
        
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            marker=dict(size=12, color=color, line=dict(width=2, color='black')),
            text=list(graph.nodes()),
            textposition='middle center',
            hovertemplate=f'Graph {graph_idx+1}<br>Node: %{{text}}<extra></extra>',
            name=f'Layer {graph_idx + 1}'
        ))
        
        # Update layout for 2D
        fig.update_layout(
            title=f'2D View - Graph {graph_idx + 1} ({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)',
            xaxis_title='X',
            yaxis_title='Y',
            showlegend=False,
            xaxis=dict(showgrid=True, zeroline=False),
            yaxis=dict(showgrid=True, zeroline=False),
            width=800,
            height=600,
            plot_bgcolor='white'
        )
        
        # Clear output and show new figure
        with self.output:
            self.output.clear_output(wait=True)
            fig.show()
    
    def _on_dropdown_change(self, change):
        """Handle dropdown selection change"""
        if change['new'] == '3d':
            self._show_3d()
        else:
            graph_idx = change['new']
            self._show_2d(graph_idx)
    
    def display(self):
        """Display the widget and figure"""
        display(widgets.VBox([self.dropdown, self.output]))

    def get_3d_figure(self, single_graph_index=None, json_reports=None, button_clicked=None):
        """Return the 3D figure for embedding in Dash"""
        fig = go.Figure()
        
        # If single_graph_index is specified, show only that graph
        if single_graph_index is not None:
            graphs_to_show = [self.graphs[single_graph_index]]
            layouts_to_show = [self.layouts_3d[single_graph_index]]
            colors_to_show = [self.categorical_colors[single_graph_index % len(self.categorical_colors)]]
            graph_indices = [single_graph_index]
        else:
            # Show all graphs
            graphs_to_show = self.graphs
            layouts_to_show = self.layouts_3d
            colors_to_show = self.categorical_colors
            graph_indices = list(range(len(self.graphs)))
        
        # Extract correlated SAE features from JSON reports if available
        correlated_features = {}
        if json_reports:
            for report_key, report_data in json_reports.items():
                if 'correlated_sae_features' in report_data:
                    features = report_data['correlated_sae_features']
                    correlated_features[report_key] = f"[{', '.join(map(str, features))}]"
        
        # Add graphs to figure
        for i, (graph, layout_3d, color) in enumerate(zip(graphs_to_show, layouts_to_show, colors_to_show)):
            actual_graph_index = graph_indices[i]
            
            # Add nodes
            node_x = []
            node_y = []
            node_z = []
            node_features = []
            node_colors = []
            
            # Check if this is Layer 8 (graph index 7) and we have correlated features
            is_layer_8 = actual_graph_index == 7
            has_correlated_features = bool(correlated_features)
            white_node_assigned = False
            
            for node_idx, node in enumerate(graph.nodes()):
                if node not in layout_3d:
                    continue
                x, y, z = layout_3d[node]
                node_x.append(x)
                node_y.append(y)
                node_z.append(z)
                
                # Special handling for Layer 8 with correlated features
                # Use button_clicked to determine which node gets the white color
                target_node_idx = button_clicked if button_clicked is not None else 0
                if is_layer_8 and has_correlated_features and not white_node_assigned and node_idx == target_node_idx:
                    # Make the target node white and use correlated SAE features
                    node_colors.append('white')
                    # Use features from the corresponding report (button_clicked maps to report key)
                    report_key = str(button_clicked) if button_clicked is not None else '0'
                    if report_key in correlated_features:
                        node_features.append(correlated_features[report_key])
                    else:
                        # Fallback to first available report if specific one not found
                        first_report_features = list(correlated_features.values())[0]
                        node_features.append(first_report_features)
                    white_node_assigned = True
                else:
                    # Normal node coloring and feature generation
                    node_colors.append(color)
                    # Generate 1-6 random SAE feature numbers between 1 and 32000
                    np.random.seed(actual_graph_index * 1000 + node)  # Consistent per node
                    num_features = np.random.randint(1, 7)  # 1-6 features
                    features = sorted(np.random.choice(range(1, 32001), size=num_features, replace=False))
                    node_features.append(f"[{', '.join(map(str, features))}]")

            node_trace = go.Scatter3d(
                x=node_x,
                y=node_y,
                z=node_z,
                mode='markers',
                marker=dict(
                    size=8,
                    color=node_colors,
                    line=dict(width=1, color='#1a365d')
                ),
                name=f'Layer {actual_graph_index+1}',
                hovertemplate=f'SAE features: %{{text}}<extra></extra>',
                text=node_features
            )
            fig.add_trace(node_trace)

            # Add edges
            edge_x = []
            edge_y = []
            edge_z = []
            for edge in graph.edges():
                if edge[0] not in layout_3d or edge[1] not in layout_3d:
                    continue
                x0, y0, z0 = layout_3d[edge[0]]
                x1, y1, z1 = layout_3d[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
                edge_z.extend([z0, z1, None])

            edge_trace = go.Scatter3d(
                x=edge_x,
                y=edge_y,
                z=edge_z,
                mode='lines',
                line=dict(
                    color='#2d5a87',
                    width=2
                ),
                hoverinfo='none',
                name=f'Graph {actual_graph_index+1} Edges',
                showlegend=False
            )
            fig.add_trace(edge_trace)

        # Configure layout for Dash modal
        title_text = f'SAE Knowledge Graph {single_graph_index+1}' if single_graph_index is not None else 'SAE Knowledge Graphs - All Networks'
        
        fig.update_layout(
            title={
                'text': title_text,
                'x': 0.5,
                'font': {'size': 14, 'color': '#1a365d'}
            },
            scene=dict(
                xaxis=dict(
                    title='Network Plane' if single_graph_index is None else '',
                    showbackground=False,
                    showticklabels=False if single_graph_index is not None else True,
                    showgrid=False if single_graph_index is not None else True
                ),
                yaxis=dict(
                    title='Y' if single_graph_index is None else '',
                    showbackground=False,
                    showticklabels=False if single_graph_index is not None else True,
                    showgrid=False if single_graph_index is not None else True
                ),
                zaxis=dict(
                    title='Z' if single_graph_index is None else '',
                    showbackground=False,
                    showticklabels=False if single_graph_index is not None else True,
                    showgrid=False if single_graph_index is not None else True
                ),
                aspectmode='manual',
                aspectratio=dict(x=3 if single_graph_index is None else 1, y=1, z=1),
                camera=dict(
                    center=dict(x=0, y=0, z=0),
                    eye=dict(x=1.2 if single_graph_index is not None else 0.01, 
                            y=1.2 if single_graph_index is not None else -2.5, 
                            z=1.2 if single_graph_index is not None else 0.01)
                ),
                bgcolor='rgba(0,0,0,0)'
            ),
            margin=dict(l=0, r=0, b=0, t=40),
            showlegend=True if single_graph_index is None else False,
            paper_bgcolor='rgba(0,0,0,0)',
            width=500 if single_graph_index is not None else 900,
            height=400 if single_graph_index is not None else 700
        )
        
        return fig

# Create the enhanced viewer (but don't display automatically)
# switcher = EnhancedNetworkSwitcher(graphs)  # Commented out to prevent automatic display