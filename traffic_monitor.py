from typing import List
import cv2
from inference import InferencePipeline
from inference.core.interfaces.camera.entities import VideoFrame
from ultralytics import YOLO
from utils.general import find_in_list, load_zones_config
import supervision as sv
import tkinter as tk
from tkinter import filedialog
import scripts.draw_zones as draw_zones
import scripts.stream_from_file as rtsp_stream
import sqlite3
from datetime import datetime
import time

class CustomSink:
    def __init__(self, zone_configuration_path: str, classes: List[int], weights: str, location: str):
        self.model = YOLO(weights)
        self.classes = classes
        self.location = location
        self.class_names = ['bus', 'car', 'motorcycle', 'person', 'truck']
        self.tracker = sv.ByteTrack(minimum_matching_threshold=0.8)
        self.fps_monitor = sv.FPSMonitor()
        self.line = load_zones_config(file_path=zone_configuration_path)
        self.line_zone = sv.LineZone(
            start=sv.Point(self.line[0][0][0], self.line[0][0][1]),
            end=sv.Point(self.line[0][1][0], self.line[0][1][1]),
            triggering_anchors=(sv.Position.CENTER,)
        )

        self.line_zone_annotator = sv.LineZoneAnnotator(thickness=1, text_thickness=1, text_scale=0.5)
        self.box_annotator = sv.BoxAnnotator(thickness=1, text_thickness=1, text_scale=0.5)

        self.counts = {
            'bus': {'in': 0, 'out': 0},
            'car': {'in': 0, 'out': 0},
            'motorcycle': {'in': 0, 'out': 0},
            'person': {'in': 0, 'out': 0},
            'truck': {'in': 0, 'out': 0}
        }

        self.last_update_time = time.time()
        self.update_interval = 10  # seconds

        self.connect_db()

    def connect_db(self):
        self.conn = sqlite3.connect('traffic_monitor_data.db')
        self.cursor = self.conn.cursor()
        self.create_table()
        self.initialize_counts()
        self.get_last_counts()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS traffic_counts (
                location TEXT,
                object_type TEXT,
                in_count INTEGER,
                out_count INTEGER,
                last_updated TEXT,
                PRIMARY KEY (location, object_type)
            )
        ''')
        self.conn.commit()


    def initialize_counts(self):
        for obj_type in self.counts.keys():
            self.cursor.execute('''
                INSERT OR IGNORE INTO traffic_counts (location, in_count, out_count, object_type, last_updated)
                VALUES (?, 0, 0, ?, ?)
            ''', (self.location, obj_type, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()
        
    def get_last_counts(self):
        self.cursor.execute('''
            SELECT object_type, in_count, out_count
            FROM traffic_counts
            WHERE location = ?
        ''', (self.location,))
        rows = self.cursor.fetchall()
        for row in rows:
            obj_type, in_count, out_count = row
            self.counts[obj_type]['in'] = in_count
            self.counts[obj_type]['out'] = out_count

    def update_database(self):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for obj_type, count_data in self.counts.items():
            self.cursor.execute('''
                UPDATE traffic_counts
                SET in_count = ?, out_count = ?, last_updated = ?
                WHERE object_type = ? AND location = ?
            ''', (count_data['in'], count_data['out'], current_time, obj_type, self.location))
        self.conn.commit()

    def update_counts(self, in_count_forEach_class, out_count_forEach_class):
        for obj_type in in_count_forEach_class:
            if obj_type in self.counts:
                self.counts[obj_type]['in'] += 1

        for obj_type in out_count_forEach_class:
            if obj_type in self.counts:
                self.counts[obj_type]['out'] += 1

        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            self.update_database()
            self.last_update_time = current_time

    def on_prediction(self, detections: sv.Detections, frame: VideoFrame) -> None:
        self.fps_monitor.tick()
        fps = self.fps_monitor.fps

        valid_detections_mask = find_in_list(detections.class_id, self.classes)
        detections = detections[valid_detections_mask]
        detections = self.tracker.update_with_detections(detections)
        detected_class = detections.class_id

        in_count, out_count = self.line_zone.trigger(detections)
        detected_object_in = in_count
        detected_object_out = out_count

        counted_object_in = [i for i, x in enumerate(detected_object_in) if x == True]
        in_count_forEach_class = [self.class_names[detected_class[i]] for i in counted_object_in]

        counted_object_out = [i for i, x in enumerate(detected_object_out) if x == True]
        out_count_forEach_class = [self.class_names[detected_class[i]] for i in counted_object_out]

        self.update_counts(in_count_forEach_class, out_count_forEach_class)

        annotated_frame = frame.image.copy()

        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"FPS: {fps:.1f}",
        #     text_anchor=sv.Point(45, 20),
        #     background_color=sv.Color.from_hex("#A351FB"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )
        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"Cars in : {self.counts['car']['in']}",
        #     text_anchor=sv.Point(60, 60),
        #     background_color=sv.Color.from_hex("#ff2919"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )
        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"Motos in: {self.counts['motorcycle']['in']}",
        #     text_anchor=sv.Point(60, 100),
        #     background_color=sv.Color.from_hex("#c97771"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )
        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"Buses in: {self.counts['bus']['in']}",
        #     text_anchor=sv.Point(60, 140),
        #     background_color=sv.Color.from_hex("#ffb60a"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )
        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"Trucks in: {self.counts['truck']['in']}",
        #     text_anchor=sv.Point(60, 180),
        #     background_color=sv.Color.from_hex("#ff700a"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )
        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"Persons in: {self.counts['person']['in']}",
        #     text_anchor=sv.Point(60, 220),
        #     background_color=sv.Color.from_hex("#ff700a"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )

        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"Cars out : {self.counts['car']['out']}",
        #     text_anchor=sv.Point(60, 260),
        #     background_color=sv.Color.from_hex("#ff2919"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )
        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"Motos out: {self.counts['motorcycle']['out']}",
        #     text_anchor=sv.Point(60, 300),
        #     background_color=sv.Color.from_hex("#c97771"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )
        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"Buses out: {self.counts['bus']['out']}",
        #     text_anchor=sv.Point(60, 340),
        #     background_color=sv.Color.from_hex("#ffb60a"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )
        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"Trucks out: {self.counts['truck']['out']}",
        #     text_anchor=sv.Point(60, 380),
        #     background_color=sv.Color.from_hex("#ff700a"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )
        # annotated_frame = sv.draw_text(
        #     scene=annotated_frame,
        #     text=f"Persons out: {self.counts['person']['out']}",
        #     text_anchor=sv.Point(60, 420),
        #     background_color=sv.Color.from_hex("#ff700a"),
        #     text_color=sv.Color.from_hex("#000000"),
        # )

        labels = [
            f"# {self.model.model.names[class_id]} {confidence:.2f}"
            for confidence, class_id in zip(detections.confidence, detections.class_id)
        ]
        annotated_frame = self.line_zone_annotator.annotate(
            frame=annotated_frame,
            line_counter=self.line_zone
        )
        annotated_frame = self.box_annotator.annotate(
            scene=annotated_frame,
            detections=detections,
            labels=labels
        )

        cv2.imshow("Processed Video", annotated_frame)
        cv2.waitKey(1)

def start_pipeline(rtsp_url, zone_configuration_path, weights, processor, location):
    model = YOLO(weights)

    def inference_callback(frame: VideoFrame) -> sv.Detections:
        results = model(frame.image, verbose=False, conf=0.5, device=processor)[0]
        return sv.Detections.from_ultralytics(results).with_nms(threshold=0.5)

    sink = CustomSink(zone_configuration_path=zone_configuration_path, classes=[], weights=weights, location=location)

    pipeline = InferencePipeline.init_with_custom_logic(
        video_reference=rtsp_url,
        on_video_frame=inference_callback,
        on_prediction=sink.on_prediction,
    )

    pipeline.start()

    try:
        pipeline.join()
    except KeyboardInterrupt:
        pipeline.terminate()

def open_file_dialog():
    return filedialog.askopenfilename()

def open_directory_dialog():
    return filedialog.askdirectory()

def main():
    root = tk.Tk()
    root.title("Traffic Monitoring")    
    
    tk.Label(root, text="Video for Simulate RTSP Stream").grid(row=0)
    tk.Label(root, text="Number of Streams").grid(row=1)
    tk.Label(root, text="Source Video for Draw Line").grid(row=2)
    tk.Label(root, text="Line Configuration (Output Dir)").grid(row=3)
    tk.Label(root, text="RTSP URL").grid(row=5)
    tk.Label(root, text="YOLO").grid(row=6)
    tk.Label(root, text="cpu/mps/cuda").grid(row=7)
    tk.Label(root, text="Location").grid(row=8)

    video_stream_rtsp_entry = tk.Entry(root)
    number_of_streams_entry = tk.Entry(root)
    source_video_entry = tk.Entry(root)
    line_config_path_entry = tk.Entry(root)
    rtsp_url_entry = tk.Entry(root)
    rtsp_url_entry.insert(0, "rtsp://localhost:8554/live0.stream")
    weights_entry = tk.Entry(root) 
    processor_entry = tk.Entry(root)
    location_entry = tk.Entry(root)
    
    video_stream_rtsp_entry.grid(row=0, column=1)
    number_of_streams_entry.grid(row=1, column=1)
    source_video_entry.grid(row=2, column=1)
    line_config_path_entry.grid(row=3, column=1)
    rtsp_url_entry.grid(row=5, column=1)
    weights_entry.grid(row=6, column=1)
    processor_entry.grid(row=7, column=1)
    location_entry.grid(row=8, column=1)
    
    def video_stream_rtsp_browse_file():
        filename = open_directory_dialog()
        video_stream_rtsp_entry.insert(0, filename)
        
    video_stream_rtsp_browse_button = tk.Button(root, text="Browse", command=video_stream_rtsp_browse_file)
    video_stream_rtsp_browse_button.grid(row=0, column=2)
    
    def rtsp_stream_button_clicked():
        video_stream_path = video_stream_rtsp_entry.get()
        number_of_streams = number_of_streams_entry.get()
        root.destroy()
        rtsp_stream.main(video_stream_path, int(number_of_streams))
        
    rtsp_stream_button = tk.Button(root, text="Start RTSP Stream", command=rtsp_stream_button_clicked)
    rtsp_stream_button.grid(row=0, column=3)
        
    def source_video_browse_file():
        filename = open_file_dialog()
        source_video_entry.insert(1, filename)
        
    source_video_browse_button = tk.Button(root, text="Browse", command=source_video_browse_file)
    source_video_browse_button.grid(row=2, column=2)
    
    def line_config_browse_file():
        filename = open_directory_dialog()
        line_config_path_entry.insert(2, filename)
        
    line_config_browse_button = tk.Button(root, text="Browse", command=line_config_browse_file)
    line_config_browse_button.grid(row=3, column=2)
    
    def draw_line_button_clicked():
        source_video_path = source_video_entry.get()
        line_config_path = line_config_path_entry.get()
        line_config_path += "/config.json"
        draw_zones.main(source_video_path, line_config_path)
        
    
    draw_line_button = tk.Button(root, text="Draw Line", command=draw_line_button_clicked)
    draw_line_button.grid(row=4, columnspan=4)
        
    def yolo_weights_browse_file():
        filename = open_file_dialog()
        weights_entry.insert(3, filename)
    
    weights_browse_button = tk.Button(root, text="Browse", command=yolo_weights_browse_file)
    weights_browse_button.grid(row=6, column=2)

    def start_button_clicked():
        rtsp_url = rtsp_url_entry.get()
        line_config_path = line_config_path_entry.get()
        line_config_path += "/config.json"
        weights = weights_entry.get()
        processor = processor_entry.get()
        location = location_entry.get()
        
        root.destroy()
        start_pipeline(rtsp_url, line_config_path, weights, processor, location)

    start_button = tk.Button(root, text="Start", command=start_button_clicked)
    start_button.grid(row=9, columnspan=4)

    root.mainloop()
if __name__ == "__main__":
    main()