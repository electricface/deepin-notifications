#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 ~ 2013 Deepin, Inc.
#               2011 ~ 2013 Wang Yaohua
# 
# Author:     Wang Yaohua <mr.asianwang@gmail.com>
# Maintainer: Wang Yaohua <mr.asianwang@gmail.com>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import webbrowser

from dtk.ui.label import Label
from dtk.ui.button import Button, ImageButton
from dtk.ui.draw import draw_text, draw_hlinear, draw_round_rectangle
from dtk_cairo_blur import gaussian_blur
from dtk.ui.utils import (propagate_expose, color_hex_to_cairo, container_remove_all,
                          is_in_rect, alpha_color_hex_to_cairo)


import gtk
import cairo
import pango
import gobject

from ui.window_view import DetailViewWindow
from ui.skin import app_theme
from ui.utils import root_coords_to_widget_coords, render_hyperlink_support_text, draw_round_rectangle_with_triangle

ARROW_WIDHT = 10
ARROW_HEIGHT = 5
ROUND_RADIUS = 10

BORDER_LINE_WIDTH = 5
WINDOW_WIDHT = 300 + 2 * BORDER_LINE_WIDTH 
WINDOW_HEIGHT = 400 + 2 * BORDER_LINE_WIDTH

LIST_HEIGHT = 70
LIST_PADDING = 5
LIST_CONTENT_HEIGHT = 50
LIST_TIME_WIDTH = 100

COUNT_PER_PAGE = 2

COLOR_BLUE = "#d2f9fe"

class ListItem(gtk.EventBox):
    '''
    class docs
    '''
	
    def __init__(self, message, time):
        '''
        init docs
        '''
        gtk.EventBox.__init__(self)
        self.set_visible_window(False)
        
        self.message = message
        self.time = time
        
        self.set_size_request(-1, LIST_HEIGHT)
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.POINTER_MOTION_MASK)
        
        self.pointer_hand_rectangles = []
        
        self.connect("expose-event", self.on_expose_event)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("button-press-event", self.on_button_press)
        
        
    def on_expose_event(self, widget, event):
        cr = widget.window.cairo_create()
        rect = widget.allocation
        cr.translate(rect.x, rect.y) # only the toplevel window has the gtk.gdk.window? all cr location is relative to it?
        
        draw_round_rectangle(cr, 0, 0, rect.width, rect.height, 5)
        cr.set_source_rgb(*color_hex_to_cairo("#b2b2b2"))
        cr.fill()
        
        render_hyperlink_support_text(self, cr, self.message.body, 
                              0 + LIST_PADDING , 0,
                              rect.width - LIST_PADDING * 2, LIST_CONTENT_HEIGHT,
                              wrap_width = rect.width - LIST_PADDING * 2,
                              clip_line_count = 3,
                              alignment=pango.ALIGN_LEFT)    
        
        draw_hlinear(cr, 0, 0 + LIST_CONTENT_HEIGHT, rect.width, 1, [(0, ("#ffffff", 0)),
                                                                     (0.5, ("#2b2b2b", 0.5)), 
                                                                     (1, ("#ffffff", 0))])
        
        time = self.time.split("-")[1]
        draw_text(cr, time, 0 + LIST_PADDING, 
                  0 + LIST_CONTENT_HEIGHT , LIST_TIME_WIDTH, rect.height - LIST_CONTENT_HEIGHT)
        
    def on_motion_notify(self, widget, event):
        '''
        docs
        '''
        x = event.x
        y = event.y
        flag = False
        
        
        for rect in self.pointer_hand_rectangles:
            if is_in_rect((x, y), rect):
                flag = True
                break
            
        if flag:
            widget.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND1))
        else:
            widget.window.set_cursor(None)

            
    def on_button_press(self, widget, event):
        x = event.x
        y = event.y
        
        if event.button == 1:
            for index, rect in enumerate(self.pointer_hand_rectangles):
                if is_in_rect((x, y), rect):
                    action = self.message["hints"]["x-deepin-hyperlinks"][index]
                    
                    if action.has_key("href"):
                        webbrowser.open_new_tab(action.get("href"))
                        
                        return

    
        

class TrayPop(gtk.Window):
    '''
    class docs
    '''
	
    def __init__(self, x, y, items):
        '''
        init docs
        '''
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        
        self.x, self.y = x - WINDOW_WIDHT / 2, y - WINDOW_HEIGHT
        self.set_size_request(WINDOW_WIDHT, WINDOW_HEIGHT)
        self.set_colormap(gtk.gdk.Screen().get_rgba_colormap() or gtk.gdk.Screen().get_rgb_colormap())
        self.set_keep_above(True)
        
        self.move(self.x, self.y)
        self.__init_view(items)
        
        self.connect("expose-event", self.on_expose_event)
        

        
    def __init_view(self, items):
        main_box = gtk.VBox()
        main_box_align = gtk.Alignment(1, 1, 1, 1)
        main_box_align.set_padding(10, 10, 10, 10)
        main_box_align.add(main_box)
        
        header_box = gtk.HBox()
        title_label = Label("Message View")
        settings_button = SettingButton()
        settings_button.connect("clicked", self.on_settings_button_clicked)
        header_box.pack_start(title_label, False, False)
        header_box.pack_end(settings_button, False, False)
        
        self.view_flipper = ViewFlipper(items)
        self.flipper_align = gtk.Alignment(0.5, 0.5, 1, 1)
        self.flipper_align.connect("expose-event", self.on_flipper_align_expose)
        self.flipper_align.set_padding(5, 5, 10, 10)
        self.flipper_align.add(self.view_flipper)
        
        footer_box = gtk.HBox()
        self.left_button = Button("&lt;")
        self.left_button.set_size_request(50, 20)
        self.left_button.connect("clicked", self.on_left_btn_clicked)
        self.right_button = Button("&gt;")
        self.right_button.set_size_request(50, 20)
        self.right_button.connect("clicked", self.on_right_btn_clicked)        

        footer_box.pack_start(self.left_button, False, False, 5)
        footer_box.pack_end(self.right_button, False, False, 5)
        
        main_box.pack_start(header_box, False, False, 5)
        main_box.pack_start(self.flipper_align)
        main_box.pack_end(footer_box, False, False, 5)
        
        self.add(main_box_align)
        
        
    def on_flipper_align_expose(self, widget, event):
        cr = widget.window.cairo_create()
        rect = widget.allocation
        
        draw_hlinear(cr, rect.x, rect.y + rect.height, rect.width, 1, [(0, ("#ffffff", 0)),
                                                                       (0.5, ("#2b2b2b", 0.5)), 
                                                                       (1, ("#ffffff", 0))])
        
    def pointer_grab(self):
        gtk.gdk.pointer_grab(
            self.window,
            True,
            gtk.gdk.BUTTON_PRESS_MASK,
            None,
            None,
            gtk.gdk.CURRENT_TIME)
        
        gtk.gdk.keyboard_grab(
                self.window, 
                owner_events=False, 
                time=gtk.gdk.CURRENT_TIME)
        
        self.grab_add()
        self.connect("button-press-event", self.on_button_press)
        
    def pointer_ungrab(self):
        gtk.gdk.pointer_ungrab(gtk.gdk.CURRENT_TIME)
        gtk.gdk.keyboard_ungrab(gtk.gdk.CURRENT_TIME)
        self.grab_remove()
        
    def on_button_press(self, widget, event):
        ex, ey =  event.x, event.y
        rect = self.allocation
        
        if not is_in_rect((ex, ey), rect):
            self.dismiss()

    def on_settings_button_clicked(self, widget):
        DetailViewWindow().show_all()
        
        
    def on_left_btn_clicked(self, widget):
        self.view_flipper.flip_backward()
    
    
    def on_right_btn_clicked(self, widget):
        self.view_flipper.flip_forward()
    
        
    def on_expose_event(self, widget, event):
        '''
        docs
        '''
        cr = widget.window.cairo_create()
        rect = widget.allocation
        
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.rectangle(*rect)
        cr.fill()
    
        
        # trayicon's location is relavant to root, but cairo need coordinates related to this widget.
        (self.x, self.y) = root_coords_to_widget_coords(self.x, self.y, self)
        
        
        # draw border and blur
        img_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, WINDOW_WIDHT, WINDOW_HEIGHT)
        img_surf_cr = cairo.Context(img_surf)
        draw_round_rectangle_with_triangle(img_surf_cr, rect.x + BORDER_LINE_WIDTH, rect.y + BORDER_LINE_WIDTH,
                                           rect.width - 2 * BORDER_LINE_WIDTH, 
                                           rect.height - 2 * BORDER_LINE_WIDTH,
                                           ROUND_RADIUS, ARROW_WIDHT, ARROW_HEIGHT)
        
        img_surf_cr.set_line_width(1)
        img_surf_cr.stroke()
        gaussian_blur(img_surf, 2)
        
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_surface(img_surf, 0, 0)
        cr.rectangle(*rect)
        cr.fill()
        
        #draw content background
        draw_round_rectangle_with_triangle(cr, rect.x + BORDER_LINE_WIDTH, rect.y + BORDER_LINE_WIDTH,
                                           rect.width - 2 * BORDER_LINE_WIDTH, 
                                           rect.height - 2 * BORDER_LINE_WIDTH,
                                           ROUND_RADIUS, ARROW_WIDHT, ARROW_HEIGHT)
        cr.set_source_rgb(1, 1, 1)
        cr.fill()

        
        propagate_expose(widget, event)
        
        return True
    
    def show_up(self):
        self.show_all()
        self.pointer_grab()
        
    def dismiss(self):
        self.destroy()
        self.pointer_ungrab()
    
gobject.type_register(TrayPop)    