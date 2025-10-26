import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import Dash, dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import calendar
from scipy.ndimage import gaussian_filter1d


# Bootstrap formatting
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# fully cleaned dataset
df = pd.read_csv('data/cleaned_disaster_data.csv')


# disaster type categories
disaster_categories = {
    'Geophysical': ['Earthquake', 'Volcanic activity', 'Mass movement (dry)'],
    'Meteorological': ['Storm', 'Extreme temperature'],
    'Hydrological': ['Flood', 'Mass movement (wet)'],
    'Climatological': ['Drought', 'Wildfire'],
    'Biological': ['Epidemic']
}

# categories for dropdown options
disaster_options = [{'label': 'All Disasters', 'value': 'all'}]
for category, types in disaster_categories.items():
    disaster_options.append({'label': f'--- {category} ---', 'value': category, 'disabled': True})
    for dtype in types:
        disaster_options.append({'label': dtype, 'value': dtype})

# impact metrics options
impact_options = [
    {'label': 'Number of Events', 'value': 'count'},
    {'label': 'Total Deaths', 'value': 'Total Deaths'},
    {'label': 'Total Affected', 'value': 'Total Affected'}
]



# LAYOUT:
app.layout = dbc.Container([
    # title:
    dbc.Row([
        dbc.Col([
            html.H1("Global Natural Disasters Impacts Explorer", className="text-center my-4"),
            html.P("Patterns and impacts of natural disasters worldwide from 1900-2024", 
                   className="text-center text-muted mb-4"),
        ], width=12)
    ]),
    
    # ROW 1: global filters:
    dbc.Row([
        dbc.Col([
            html.Label("Disaster Type", className="filter-label"),
            dcc.Dropdown(
                id='disaster-type',
                options=disaster_options,
                value='all',
                clearable=False
            ),
        ], width=3),
        
        dbc.Col([
            html.Label("Year Range", className="filter-label"),
            dcc.RangeSlider(
                id='year-range',
                min=1900,
                max=2023,
                value=[1980, 2023],
                marks={i: str(i) for i in range(1900, 2024, 20)},
                step=1
            )
        ], width=6),
        
        dbc.Col([
            html.Label("Impact Metric To Visualize", className="filter-label"),
            dcc.RadioItems(
                id='impact-metric',
                options=impact_options,
                value='Total Deaths',
                inline=False
            )
        ], width=3)
    ], className="mb-4 filters-row"),


    # Selected country info (hidden at first)
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H3(id="selected-country-header", children="Global Overview", className="d-inline"),
                html.Button("Reset to Global", id="reset-button", 
                           className="btn btn-outline-secondary ms-3", style={"display": "none"})
            ]),
            html.Div(id="country-stats", className="lead")
        ], width=12)
    ], className="mb-3"),
    
    # 1ST ROW: MAP AND CHARTS ROW (MAP ON LEFT, PIE CHART & HEATMAP ON RIGHT)
    dbc.Row([
        # Left column with map and regional barchart
        dbc.Col([
            # Choropleth map
            dbc.Card([
                dbc.CardHeader("Geographic Distribution"),
                dbc.CardBody([
                    dcc.Graph(id='choropleth-map', style={'height': '55vh'})
                ])
            ], className="graph-card"),
            # regional barchart below map
            dbc.Card([
                dbc.CardHeader("Regional Impact Differences"),
                dbc.CardBody([
                    dcc.Graph(id='regional-impact', style={'height': '70vh'})
                ]),
                # Add the caption text 
                html.P("Regional aggregation excludes countries with insufficient data coverage", 
                       className="text-muted small px-3 pb-2 mb-0", 
                       style={"font-size": "0.8rem"})
            ], className="graph-card")
        ], width=7),
        
        # Right column with pie chart and heatmap
        dbc.Col([
            # Pie chart
            dbc.Card([
                dbc.CardHeader("Disaster Type Distribution"),
                dbc.CardBody([
                    dcc.Graph(id='disaster-piechart', style={'height': '50vh'})
                ])
            ], className="graph-card"),
            
            # Heatmap below pie chart
            dbc.Card([
                dbc.CardHeader("Seasonal Patterns"),
                dbc.CardBody([
                    dcc.Graph(id='seasonal-heatmap', style={'height': '60vh'})
                ])
            ], className="graph-card")
        ], width=5)
    ], className="mb-4"),
    
# ANOTHER CHARTS ROW: TIME SERIES LINEGRAPH
dbc.Row([
    dbc.Col([
        dbc.Card([
            dbc.CardHeader("Disaster Trends Over Time"),
            dbc.CardBody([
                dcc.Graph(id='time-series', style={'height': '60vh'})
            ])
        ], className="graph-card mb-0"),
        # slider for smoothing below linegraph
        html.Div([
            html.Div([
                html.Label("Line Smoothing", style={"margin-bottom": "2px", "font-size": "0.9rem", "text-align": "center", "width": "100%"}),
                dcc.Slider(
                    id='smoothing-slider',
                    min=1,
                    max=5,
                    step=0.1,
                    value=1,
                    marks={i: str(i) for i in range(1, 6)},
                    tooltip={"placement": "bottom", "always_visible": True}
                )
            ], className="d-flex flex-column")
        ], className="slider-container mx-auto my-3", style={"width": "50%", "padding": "5px"})
    ], width=12) # full width for the time series
], className="mb-4"),
    
    # ending insights section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("KEY TAKEAWAYS", style={"font-size": "1.5rem", "font-weight": "bold"}),
                dbc.CardBody([
                    html.Div(id="insights-content")
                ])
            ])
        ], width=12)
    ], className="mb-4"),
    
# DATA SOURCE:
dbc.Row([
    dbc.Col([
        html.P([
            "Data source: EM-DAT International Disaster Database",
            html.Br(),
            "By Hannah Siegel"
        ], className="text-muted text-center")
    ], width=12)
])
], fluid=True)




# callbacks for interactive graphs
@app.callback(
    [Output('choropleth-map', 'figure'),
     Output('selected-country-header', 'children'),
     Output('country-stats', 'children'),
     Output('reset-button', 'style')],
    [Input('disaster-type', 'value'),
     Input('year-range', 'value'),
     Input('impact-metric', 'value'),
     Input('choropleth-map', 'clickData'),
     Input('reset-button', 'n_clicks')],
    [State('selected-country-header', 'children')]
)


# MAP UPDATES: select certain countries, filter by other filters (metric, year range, disaster type)
def update_map(disaster_type, year_range, impact_metric, click_data, reset_clicks, current_header):
    # Filter by year range, disaster type
    filtered_df = df[(df['Start Year'] >= year_range[0]) & (df['Start Year'] <= year_range[1])]
    
    if disaster_type != 'all':
        if disaster_type in disaster_categories:
            filtered_df = filtered_df[filtered_df['Disaster Type'].isin(disaster_categories[disaster_type])]
        else:
            filtered_df = filtered_df[filtered_df['Disaster Type'] == disaster_type]
    
    # HANDLING COUNTRY CLICKS:
    # no clicks at first
    if reset_clicks is None:
        reset_clicks = 0
    
    # if reset button was clicked
    if reset_clicks > 0:
        selected_country = None
        header = "Global Overview"
        reset_button_style = {"display": "none"}
    
    # if a country was clicked on the map:
    elif click_data is not None:
        selected_country = click_data['points'][0]['location']
        header = f"Focus: {selected_country}"
        reset_button_style = {"display": "inline-block"}
    
    else: # if no new clicks, keep previous state
        if 'Focus:' in current_header:
            selected_country = current_header.replace('Focus: ', '')
            header = current_header
            reset_button_style = {"display": "inline-block"}
        else:
            selected_country = None
            header = "Global Overview"
            reset_button_style = {"display": "none"}
    
    # filter data by country if selected
    if selected_country:
        country_df = filtered_df[filtered_df['Country'] == selected_country]
    else:
        country_df = filtered_df
    
    # groupby country, aggregate metric (count, deaths, etc) for choropleth mapping:
    if impact_metric == 'count':
        country_stats = filtered_df.groupby('Country').size().reset_index(name='value')
    else:
        country_stats = filtered_df.groupby('Country')[impact_metric].sum().reset_index(name='value')
    
    # Choropleth map
    fig_choropleth = px.choropleth(
        country_stats,
        locations='Country',
        locationmode='country names',
        color='value',
        hover_name='Country',
        color_continuous_scale='Reds',
        title=f'Impact of {disaster_type if disaster_type != "all" else "All"} Disasters ({year_range[0]}-{year_range[1]})',
        labels={'value': impact_metric.title() if impact_metric == 'count' else impact_metric}, 
        hover_data={'value': True, 'Country': False} # only show value, hide 'Country'
    )
    
    fig_choropleth.update_layout(
        geo=dict(showcoastlines=True, projection_type='natural earth'),
        margin=dict(t=40, r=0, l=0, b=0),
        coloraxis_colorbar=dict(title=impact_metric.title())
    )

    
    # stats for selected country or global
    if selected_country:
        total_events = len(country_df)
        most_common = country_df['Disaster Type'].value_counts().idxmax() if total_events > 0 else "N/A"
        worst_year = country_df.groupby('year').size().idxmax() if total_events > 0 else "N/A"
        total_deaths = country_df['Total Deaths'].sum()
        total_affected = country_df['Total Affected'].sum()
        
        stats = [
            f"Total disaster events: {total_events:,.0f}",
            f"Most common disaster type: {most_common}",
            f"Year with most disaster events: {worst_year}",
            f"Total deaths: {total_deaths:,.0f}",
            f"Total affected: {total_affected:,.0f}"
        ]
    else:
        total_events = len(filtered_df)
        stats = [
            f"Showing data for {year_range[0]}-{year_range[1]}",
            f"Total disaster events worldwide: {total_events:,}",
            f"Use the map to select a specific country for detailed analysis"
        ]
    
    return fig_choropleth, header, html.P(", ".join(stats)), reset_button_style

@app.callback(
    [Output('time-series', 'figure'),
     Output('disaster-piechart', 'figure'),
     Output('regional-impact', 'figure'),
     Output('seasonal-heatmap', 'figure'),
     Output('insights-content', 'children')],
    [Input('disaster-type', 'value'),
     Input('year-range', 'value'),
     Input('impact-metric', 'value'),
     Input('selected-country-header', 'children'), 
     Input('smoothing-slider', 'value')] # slider
)


# FILTER/UPDATE every other figure by disaster type, year, and metric selections:
def update_visualizations(disaster_type, year_range, impact_metric, header, smoothing_window):
    # update header/text to show selected country
    selected_country = None
    if 'Focus:' in header:
        selected_country = header.replace('Focus: ', '')
    
    # Filter data:
    filtered_df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]
    
    if disaster_type != 'all':
        if disaster_type in disaster_categories:
            filtered_df = filtered_df[filtered_df['Disaster Type'].isin(disaster_categories[disaster_type])]
        else:
            filtered_df = filtered_df[filtered_df['Disaster Type'] == disaster_type]
    
    # filter by country if selected
    if selected_country:
        country_df = filtered_df[filtered_df['Country'] == selected_country]
    else:
        country_df = filtered_df
    
    # TIME SERIES:
    if impact_metric == 'count':
        time_series = country_df.groupby(['year', 'Disaster Type']).size().reset_index(name='value')
    else:
        time_series = country_df.groupby(['year', 'Disaster Type'])[impact_metric].sum().reset_index(name='value')

    # Smoothing:
    for disaster in time_series['Disaster Type'].unique():
        mask = time_series['Disaster Type'] == disaster
        if sum(mask) > 3: # Only smooth if we have enough points
            # Convert smoothing_window to sigma (lower = less smoothing)
            sigma = smoothing_window / 3
            # Apply Gaussian smoothing
            time_series.loc[mask, 'smoothed_value'] = gaussian_filter1d(
                time_series.loc[mask, 'value'], sigma=sigma
            )
        else:
            # Not enough points: use original values
            time_series.loc[mask, 'smoothed_value'] = time_series.loc[mask, 'value']

    fig_timeseries = px.line(
        time_series,
        x='year',
        y='smoothed_value',
        color='Disaster Type',
        title=f"{impact_metric if impact_metric != 'count' else 'Number of Events'} Over Time {f'in {selected_country}' if selected_country else 'Worldwide'}",
        labels={'year': 'Year', 'smoothed_value': impact_metric if impact_metric != 'count' else 'Number of Events'}, 
        hover_data={
        'year': True,
        'smoothed_value': ':.0f',
        'Disaster Type': True
    }
    )
    
    fig_timeseries.update_layout(
        xaxis_title='Year',
        yaxis_title=impact_metric if impact_metric != 'count' else 'Number of Events',
        legend_title='Disaster Type',
        hovermode='closest', 
        margin=dict(l=20, r=20, t=30, b=6)
    )


    # Disaster Type PIECHART:
    if impact_metric == 'count':
        disaster_piechart = country_df.groupby('Disaster Type').size().reset_index(name=impact_metric)
    else:
        disaster_piechart = country_df.groupby('Disaster Type')[impact_metric].sum().reset_index(name=impact_metric)

    # Calculating "Other" category:
    disaster_piechart = disaster_piechart.sort_values(impact_metric, ascending=False) # sort
    total_value = disaster_piechart[impact_metric].sum()
    threshold = 0.02 * total_value # bottom 2% of the total

    # Separate disasters into major & other (under 2%)
    major_disasters = disaster_piechart[disaster_piechart[impact_metric] >= threshold]
    other_disasters = disaster_piechart[disaster_piechart[impact_metric] < threshold]
    if not other_disasters.empty:
        other_row = pd.DataFrame({'Disaster Type': ['Other'], impact_metric: [other_disasters[impact_metric].sum()]})
        disaster_piechart = pd.concat([major_disasters, other_row], ignore_index=True)

    # Pie chart:
    fig_piechart = px.pie(
        disaster_piechart,
        values=impact_metric,
        names='Disaster Type',
        title=f"Distribution of {impact_metric if impact_metric != 'count' else 'Number of Events'} by Disaster Type {f'in {selected_country}' if selected_country else 'Worldwide'}",
        hole=0.4, 
        hover_data={impact_metric: True}
    )

    fig_piechart.update_layout(
        legend_title='Disaster Type', 
        hovermode='closest',
        margin=dict(l=20, r=20, t=40, b=5),
        title={
        'y':0.95,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top',
        'font': {'size': 15}
    }
    )

    
    # BY-REGION BARCHART:
    if selected_country:
        selected_country_region = df[df['Country'] == selected_country]['Region'].iloc[0]
        regional_countries = df[df['Region'] == selected_country_region]['Country'].unique() # get all countries in that region
        # Filter data to that region
        regional_df = filtered_df[filtered_df['Country'].isin(regional_countries)]
        
        # Group by country and disaster type
        if impact_metric == 'count':
            # First, get total value by country to determine top countries
            country_totals = regional_df.groupby('Country').size().reset_index(name='total')
            regional_impact = regional_df.groupby(['Country', 'Disaster Type']).size().reset_index(name='value')
        else:
            # First, get total value by country to determine top countries
            country_totals = regional_df.groupby('Country')[impact_metric].sum().reset_index(name='total')
            regional_impact = regional_df.groupby(['Country', 'Disaster Type'])[impact_metric].sum().reset_index(name='value')
        
        # Sort countries by total value
        country_totals = country_totals.sort_values('total', ascending=False)
        
        # Take top N countries
        top_n = 6 # top 6 countries
        # Always include the selected country
        top_countries = country_totals.head(top_n)['Country'].tolist()
        if selected_country not in top_countries:
            top_countries.append(selected_country)
    
        # separate into top countries and "Other"
        top_data = regional_impact[regional_impact['Country'].isin(top_countries)]
        other_data = regional_impact[~regional_impact['Country'].isin(top_countries)]
        # "Other (combined)" category
        if not other_data.empty and len(country_totals) > top_n + 1:  # Only create "Other" if we have more than top_n+1 countries
            other_grouped = other_data.groupby('Disaster Type')['value'].sum().reset_index()
            other_grouped['Country'] = 'Other (Combined)'
            regional_impact = pd.concat([top_data, other_grouped], ignore_index=True)
        else:
            regional_impact = top_data
        
        x_column = 'Country'
        title_location = f"{selected_country_region} Region"
    else:
        # for global view, show by region
        if impact_metric == 'count':
            regional_impact = filtered_df.groupby(['Region', 'Disaster Type']).size().reset_index(name='value')
        else:
            regional_impact = filtered_df.groupby(['Region', 'Disaster Type'])[impact_metric].sum().reset_index(name='value')
        
        x_column = 'Region'
        title_location = "Global Regions"

    category_order = regional_impact[x_column].unique().tolist()
    if 'Other (Combined)' not in category_order:
        category_order.append('Other (Combined)')

    fig_regional = px.bar(
        regional_impact,
        x=x_column,
        y='value',
        color='Disaster Type',
        title=f"{impact_metric.capitalize() if impact_metric != 'count' else 'Number of Events'} by Country in {title_location}",
        labels={x_column: x_column, 'value': impact_metric if impact_metric != 'count' else 'Number of Events'},
        barmode='group'
    )
    
    fig_regional.update_layout(
        xaxis_title=x_column,
        yaxis_title=impact_metric if impact_metric != 'count' else 'Number of Events',
        legend_title='Disaster Type',
        xaxis={'categoryorder': 'array', 'categoryarray': category_order}, 
        margin=dict(l=30, r=30, t=30, b=5)
    )


    # SEASONAL HEATMAP:
    if 'month' in country_df.columns and not country_df['month'].isna().all(): # check for month data
        # choose the metric / column for aggregation
        if impact_metric == 'count':
            seasonal = country_df.groupby(['month', 'Disaster Type']).size().reset_index(name='value') # count
        else:
            seasonal = country_df.groupby(['month', 'Disaster Type'])[impact_metric].sum().reset_index(name='value') # sum
    
        # pivot df for heatmap
        try:
            seasonal_pivot = seasonal.pivot(index='Disaster Type', columns='month', values='value').fillna(0)
            # month labels
            month_labels = [calendar.month_abbr[i] if i in seasonal_pivot.columns else '' for i in range(1, 13)]
    
            # PLOT HEATMAP
            fig_heatmap = px.imshow(
                seasonal_pivot,
                x=month_labels,
                y=seasonal_pivot.index,
                color_continuous_scale='YlOrRd',
                title=f'Seasonal Patterns of Disasters {f"in {selected_country}" if selected_country else "Worldwide"}',
                labels=dict(x='Month', y='Disaster Type', color=impact_metric)
            )
    
            fig_heatmap.update_layout(
                xaxis_title='Month',
                yaxis_title='Disaster Type',
                margin=dict(l=30, r=30, t=30, b=5)
            )
        except:
            # fallback: barplot if pivot fails
            fig_heatmap = px.bar(
                seasonal,
                x='month',
                y='value',
                color='Disaster Type',
                title=f'Monthly Distribution of {impact_metric} {f"in {selected_country}" if selected_country else "Worldwide"}'
            )
    else:
        # fallback figure if month data is missing
        fig_heatmap = go.Figure()
        fig_heatmap.update_layout(
            title="Seasonal data not available",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False), 
            margin=dict(l=30, r=30, t=30, b=5)
        )
        fig_heatmap.add_annotation(
            text="Month-level data is required for seasonal analysis",
            showarrow=False,
            font=dict(size=14)
        )


    # FINAL INSIGHTS/TAKEAWAYS:
    insights = []
    
    # calculate metrics to present
    total_disasters = len(country_df)
    if total_disasters > 0:
        if impact_metric != 'count':
            total_impact = country_df[impact_metric].sum()
            worst_year_impact = country_df.groupby('year')[impact_metric].sum()
            worst_year = worst_year_impact.idxmax()
            worst_year_value = worst_year_impact.max()
        else:
            worst_year_count = country_df.groupby('year').size()
            worst_year = worst_year_count.idxmax() 
            worst_year_value = worst_year_count.max()
            
        most_common = country_df['Disaster Type'].value_counts().idxmax()
        most_deadly = country_df.groupby('Disaster Type')['Total Deaths'].sum().idxmax()
        most_affected = country_df.groupby('Disaster Type')['Total Affected'].sum().idxmax()
        
        # CARDS with insights
        insights = [
            dbc.Card([
                dbc.CardBody([
                    html.H5(f"Time Period Analysis", className="card-title"),
                    html.P([
                        f"During {year_range[0]}-{year_range[1]}, there were ",
                        html.Strong(f"{total_disasters:,.0f}"),
                        f" recorded disaster events{f' in {selected_country}' if selected_country else ' worldwide'}."
                    ]),
                    html.P([
                        f"The year with the highest impact was ",
                        html.Strong(f"{worst_year}"),
                        f" with {worst_year_value:,.0f} {impact_metric if impact_metric != 'count' else 'events'}."
                    ])
                ])
            ], className="mb-3"),
            
            dbc.Card([
                dbc.CardBody([
                    html.H5(f"Disaster Type Analysis", className="card-title"),
                    html.P([
                        f"The most common disaster type was ",
                        html.Strong(f"{most_common}"),
                        f", while the most deadly was ",
                        html.Strong(f"{most_deadly}"),
                        f" and the one affecting most people was ",
                        html.Strong(f"{most_affected}"),
                        "."
                    ])
                ])
            ], className="mb-3")
        ]
        
        # if country is selected, compare it to global data
        if selected_country:
            # country vs global metrics:
            country_pct = (total_disasters / len(filtered_df)) * 100
            
            # add card
            insights.append(
                dbc.Card([
                    dbc.CardBody([
                        html.H5(f"Comparative Analysis", className="card-title"),
                        html.P([
                            f"{selected_country} accounts for ",
                            html.Strong(f"{country_pct:.1f}%"),
                            f" of all disasters in the selected time period and categories."
                        ])
                    ])
                ])
            )
    
    return fig_timeseries, fig_piechart, fig_regional, fig_heatmap, insights



if __name__ == '__main__':
    app.run(debug=True, port=8051)