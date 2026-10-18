"""Illustrative route topology; never a navigational route or actual voyage assignment."""
import networkx as nx

class MaritimeNetwork:
    def __init__(self):
        self.graph=nx.Graph()
        # Approximate transit days solely for graph algorithm demonstration.
        self.graph.add_weighted_edges_from([
            ('Gulf','Hormuz',1),('Hormuz','Arabian Sea',2),('Arabian Sea','Malacca',8),
            ('Malacca','East Asia',5),('Arabian Sea','Bab el-Mandeb',4),('Bab el-Mandeb','Suez',4),
            ('Suez','Mediterranean',1),('Mediterranean','Gibraltar',4),('Gibraltar','Rotterdam',3),
            ('Arabian Sea','Cape of Good Hope',12),('Cape of Good Hope','Gibraltar',14),
            ('Rotterdam','Danish straits',2),('Danish straits','Baltic',2),
        ],weight='days')
    def route(self,origin,destination,closed=()):
        if origin not in self.graph or destination not in self.graph:raise ValueError('Unknown network node')
        if any(node not in self.graph for node in closed):raise ValueError('Unknown closure')
        active=self.graph.copy();active.remove_nodes_from(closed)
        try:
            path=nx.shortest_path(active,origin,destination,weight='days',method='dijkstra')
            return {'connected':True,'path':path,'illustrativeDays':sum(active[a][b]['days'] for a,b in zip(path,path[1:])),'basis':'illustrative topology'}
        except (nx.NetworkXNoPath,nx.NodeNotFound):return {'connected':False,'path':[],'illustrativeDays':None,'basis':'illustrative topology'}
    def centrality(self): return nx.betweenness_centrality(self.graph,weight='days')
