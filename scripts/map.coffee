
extract_map_feature = (selector) ->
    poi = $(selector)
    id: poi.attr('id')
    label: poi.find('.label').first().text()
    lat:  1 * poi.find('.geo .latitude').first().text()
    lon: 1 * poi.find('.geo .longitude').first().text()


create_icon = (imguri, scale) ->
    new OpenLayers.Icon(imguri,
                        new OpenLayers.Size(scale*32,scale*32))


map_point = (map, feat) -> 
    new OpenLayers.LonLat(feat.lon, feat.lat).transform(map.displayProjection,
                                              map.projection)


create_mark = (map, icon, feature) ->
    new OpenLayers.Marker(
        map_point(map, feature),
        icon)


add_map_feature = (map, feature, imguri, scale=1, handlers={}) ->
    mark = create_mark(map,
                       create_icon(imguri, scale),
                       feature)
    mark.event.register(evt, mark, fun) for evt, fun of handlers
    map.getLayersByName("Features")[0].addMarker(mark)


center_on_feature = (map, feature, zoom) ->
    map.setCenter(map_point(map, feature), zoom)


$ ->
    $('#map').removeClass('hidden')
    map = new OpenLayers.Map(
                'map',
                projection: new OpenLayers.Projection "EPSG:900913"
                displayProjection: new OpenLayers.Projection "EPSG:4326")
    map.addLayer(new OpenLayers.Layer.Markers "Features")
    map.addLayer(new OpenLayers.Layer.OSM.Mapnik "Mapnik")
    conf = extract_map_feature '#header'
    add_map_feature map, conf, $('#favicon').attr('href'), 1
    center_on_feature map, conf, 12


