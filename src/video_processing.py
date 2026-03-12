import ffmpeg
import os
from src import support_functions as SF
import datetime
import glob
import sys

from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.config import change_settings
change_settings({"IMAGEMAGICK_BINARY": "magick"})


class BoxingVideo:

    def __init__(self, video_file: str):
        self.file = video_file
        assert os.path.exists(self.file), f'Video file missing!: {self.file}'
        assert self.file.endswith('.mp4'), 'Only mp4 video files are supported!'
        self.probe = ffmpeg.probe(self.file)

        self.folder_name = None
        self.define_folder_name()
        self.project_dir = None
        self.create_project_folder()
        print("Video taken: "+self.folder_name)
        self.audio_file = None

        self.config = SF.get_config()

    def cut_video(self, out_video_file, start_time, end_time):
        (
            ffmpeg
            .input(self.file, ss=start_time, to=end_time)
            .output(out_video_file)
            .global_args('-loglevel', 'error')
            .run(overwrite_output=True)
        )

    def save_audio(self):
        mp3_file_name = os.path.basename(self.file).replace('.mp4','.mp3')
        self.audio_file = os.path.join(self.project_dir,mp3_file_name)
        (
            ffmpeg
            .input(self.file)
            .output(self.audio_file)
            .global_args('-loglevel', 'error')
            .run(overwrite_output=True)
        )
        print(f"MP3 file saved:{self.audio_file}")

    def cut_video_multiple(self, clips, apply_watermark=True):
        min_vid_length = self.config.getint('VIDEO','min_len')
        for i, (file_name, start, end) in enumerate(clips):
            curr_vid_length = SF.fmt_to_seconds(end) - SF.fmt_to_seconds(start)
            if curr_vid_length > min_vid_length:
                video_output = os.path.join(self.project_dir,file_name)
                (
                    ffmpeg
                    .input(self.file, ss=start, to=end)
                    .output(video_output)
                    .global_args('-loglevel', 'error')
                    .run(overwrite_output=True)
                )
                if apply_watermark:
                    add_watermark(video_output, video_output)
                print(f"{file_name} Saved")
            else:
                print(f"Video {file_name} skipped as it was too short(length:{curr_vid_length} seconds)")


    def get_metadata(self, fields: list) -> dict:

        def get_metadata(probe, field):
            fmt = probe['format']
            tags = fmt.get('tags', {})
            return fmt.get(field) or tags.get(field, 'N/A')

        out_dict = {}
        for k in fields:
            out_dict[k] = get_metadata(self.probe, k)

        return out_dict

    def define_folder_name(self):
        meta_data = self.get_metadata(['location', 'creation_time', 'duration'])

        duration_min = float(meta_data['duration'])/60
        if duration_min < 2.0:
            raise Exception("Can not process a video that is shorter than 2 mins")

        if meta_data['location'] =='N/A':
            loc_str = 'Unknown Location'
        else:
            city, state = SF.guess_city_state(meta_data['location'])
            loc_str = f'{city}, {state}'

        if meta_data['creation_time'] == 'N/A':
            time_str = datetime.datetime.now().strftime('%Y-%m-%d %I_%M%p')
        else:
            time_str = SF.get_local_time(meta_data['location'], meta_data['creation_time'])
            time_str = time_str.replace(":",'_')
        self.folder_name = time_str+" "+loc_str


    def create_project_folder(self):
        input_folder = os.path.dirname(self.file)
        output_folder = os.path.abspath(
            os.path.join(input_folder, '..', 'output'))
        full_dir = os.path.join(output_folder,self.folder_name)
        if not os.path.exists(full_dir):
            os.mkdir(full_dir)
            print(f"Project Dir: {full_dir}")
        self.project_dir = full_dir

    def check_project_status(self):
        # check if the project folder has any mp4 files
        vid_list = glob.glob(os.path.join(self.project_dir,'*.mp4'))
        if len(vid_list)>0:
            sys.exit(f"Outputs already exists in: {self.project_dir}")


def add_watermark(video_file_path, output_file_path,watermark_text=None):
    if watermark_text is None:
        watermark_text = 'Private - Do Not Share\nDo Not Post on Social Media'

    video = VideoFileClip(video_file_path, audio=True)

    watermark = (TextClip(watermark_text,
                          fontsize=80,
                          color='white',
                          font='/System/Library/Fonts/Helvetica.ttc')
                 .set_opacity(0.45)
                 .set_duration(video.duration)
                 .set_position(('center', 'center')))

    final = CompositeVideoClip([video, watermark]).set_audio(video.audio)
    final.write_videofile(output_file_path,
                          audio=True,
                          audio_codec='aac',
                          logger=None)
