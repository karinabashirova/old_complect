from lib.useful_things import *


def plot_surface(surface_object, points_objects_list=None):
    fig = go.Figure()

    fig.add_trace(go.Surface(x=surface_object.strike_prices,
                             y=surface_object.times_before_expiration,
                             z=surface_object.surface,
                             opacity=0.75, colorscale='Viridis', showscale=False))

    colors = ['red', 'tomato', 'blue', 'royalblue']
    if points_objects_list is not None:
        for i, key in enumerate(keys):
            for n in range(len(points_objects_list[key].times_before_expiration)):
                fig.add_trace(go.Scatter3d(
                    x=points_objects_list[key].strike_prices,
                    y=[points_objects_list[key].times_before_expiration[n]] * len(
                        points_objects_list[key].strike_prices),
                    z=points_objects_list[key].surface[n],
                    name=points_objects_list[key].price_type + ' ' + str(surface_object.expiration_dates[n]),
                    mode='markers', hovertext=points_objects_list[key].delta[n],
                    marker=dict(size=3, color=colors[i])))

    fig.update_layout(scene=dict(
        xaxis=dict(
            title='Strike'),
        yaxis=dict(
            title=' ',
            tickvals=surface_object.times_before_expiration,
            ticktext=surface_object.expiration_dates),

        zaxis=dict(
            title='Volatility'),
    ))

    fig.show()
