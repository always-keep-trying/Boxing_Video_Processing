import os
import librosa
import pandas as pd
import numpy as np
from datetime import datetime as dt
from scipy import signal
import matplotlib
import matplotlib.pyplot as plt
from collections import defaultdict
import shutil
from support_functions import fmt_time
base_dir = os.path.dirname(__file__)

ref_path = os.path.abspath(os.path.join(base_dir, '..','audio_ref'))
bell_file = os.path.join(ref_path,'bell_ref.mp3')
w_bell_file = os.path.join(ref_path,'warning_bell_ref.mp3')

assert all(map(os.path.exists,[bell_file,w_bell_file])), 'Reference mp3 files are missing!'


class BoxingAudio:
    def __init__(self, audio_file: str,output_path: str):
        self.file = audio_file
        assert os.path.exists(self.file), f'Audio file missing!{self.file}'
        assert self.file.endswith('.mp3'), 'Only mp3 files are supported!'

        self.output_path = output_path

        self.data = None
        self.data_lenth = None

        self.sample_rate = None
        self.times_full = None

        self.bell_file = bell_file
        self.bell_data = None

        self.warn_bell_file = w_bell_file
        self.warn_bell_data = None

        self.load()

        self.excel_file_path = None

    def load(self):
        self.data, self.sample_rate = librosa.load(self.file, sr=None)
        self.bell_data, _ = librosa.load(self.bell_file, sr=self.sample_rate)
        self.warn_bell_data, _ = librosa.load(self.warn_bell_file, sr=self.sample_rate)

        self.times_full = np.linspace(0, len(self.data) / self.sample_rate, len(self.data))

    def process(self, ref_data: np.ndarray, peak_seconds: int=10, corr_threshold: float=0.4):
        corr = signal.correlate(self.data, ref_data, mode='valid')

        # Normalize it
        norm = np.sqrt(
            signal.correlate(self.data**2, np.ones(len(ref_data)), mode='valid') *
            np.sum(ref_data**2)
        )
        normalized_corr = corr / norm  # now bounded between -1 and +1

        x = self.times_full[0:- len(ref_data) + 1]
        peaks, _ = signal.find_peaks(normalized_corr, height=corr_threshold, distance=self.sample_rate*peak_seconds)
        return list(map(int,x[peaks])), peaks, normalized_corr

    def __str__(self):
        self.data_lenth = int(len(self.data)/self.sample_rate)
        return "Audio File Length: "+fmt_time(self.data_lenth)+"(HH:MM:SS)"

    def run(self):

        self.bell_seconds, self.bell_index, self.bell_n_corr = self.process(self.bell_data)
        self.w_bell_seconds, self.w_bell_index, self.w_bell_n_corr = self.process(self.warn_bell_data)
        # summarize the time for each bell in a table
        df = pd.DataFrame()
        df.loc[:,'Type']= ['Start']+['Bell']*len(self.bell_seconds)+['Warning_Bell']*len(self.w_bell_seconds)+['End']
        df.loc[:,'Seconds'] = [0]+self.bell_seconds+self.w_bell_seconds+[int(len(self.data)/self.sample_rate)]
        df.loc[:,'Formatted_Time'] = df['Seconds'].apply(fmt_time)
        df = df.sort_values('Seconds',ascending=True,ignore_index=True)
        df.loc[:,'Delta']=df['Seconds'].diff(1)
        self.time_table_raw = df
        self.time_table_fixed = bell_time_analysis(self.time_table_raw)
        print("Bell times processed")

    @staticmethod
    def rename_output_file(out_file_name):
        _, file_extention = os.path.splitext(out_file_name)

        if os.path.exists(out_file_name):
            # if file name exists, add current timestamp to filename
            out_file_name = out_file_name.replace(file_extention,
                                                  f'_{dt.now().strftime("%Y-%m-%d_%I_%M%p")}{file_extention}')
        return out_file_name

    def save_excel(self):
        out_file_name = os.path.join(
            self.output_path,
            "Bell_Times.xlsx")

        out_file_name = self.rename_output_file(out_file_name)

        with pd.ExcelWriter(out_file_name, engine='xlsxwriter') as W:
            self.time_table_fixed.to_excel(W, sheet_name='Rounds', index=False)
            self.time_table_raw.drop(columns=['half_min']).to_excel(W, sheet_name='Raw_Times', index=False)

        print("Time tables saved to excel file in /output folder")
        self.excel_file_path = out_file_name

    def plot_signal(self):
        # run on backend
        matplotlib.use('Agg')
        f, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(14, 10))

        # Time Series for Bell
        x_bell = self.times_full[0:- len(self.bell_data) + 1]
        ax1.scatter(x_bell, self.bell_n_corr, s=1, label='Corr')
        ax1.grid()
        ax1.scatter(x_bell[self.bell_index], self.bell_n_corr[self.bell_index], marker="x",label='Bell',color='r')

        for x,y in zip(x_bell[self.bell_index], self.bell_n_corr[self.bell_index]):
            x_fmt = fmt_time(int(x))
            ax1.text(x,y,x_fmt,rotation=45,verticalalignment='bottom')

        ax1.set_title('Bell Selection')

        # Time Series for Warning Bell
        x_bell = self.times_full[0:- len(self.warn_bell_data) + 1]
        ax2.scatter(x_bell, self.w_bell_n_corr, s=1, label='Corr')
        ax2.grid()
        ax2.scatter(x_bell[self.w_bell_index], self.w_bell_n_corr[self.w_bell_index],
                    marker="x", label='Warning Bell',color='y')
        for x,y in zip(x_bell[self.w_bell_index], self.w_bell_n_corr[self.w_bell_index]):
            x_fmt = fmt_time(int(x))
            ax2.text(x,y,x_fmt,rotation=45,verticalalignment='bottom')
        ax2.set_title('Warning Bell Selection')
        plt.xlabel("Seconds")

        # time breakdown
        plt.suptitle(os.path.basename(self.file))
        png_file_path = os.path.join(
            self.output_path,
            'Audio_Bell_Selection.png')
        png_file_path = self.rename_output_file(png_file_path)
        plt.savefig(png_file_path)
        print('Bell identification plot saved on /output folder')

    def cleanup(self):
        # once the process is finished move the mp3 file from input folder to output folder
        try:
            shutil.move(self.file,os.path.join(self.output_path,os.path.basename(self.file)))
            print("Cleanup: Input file moved to output folder")
        except Exception as e:
            print(f"Cleanup process failed!: {e}")

    def main(self):
        print(self.__str__())
        self.run()
        self.plot_signal()
        self.save_excel()
        self.cleanup()

def bell_time_analysis(df: pd.DataFrame) -> pd.DataFrame:
    df['Delta'] = df['Delta'].fillna(0)
    df.loc[:, 'half_min'] = list(map(int, np.round(df['Delta'] / 30, 0)))
    df.loc[:, 'Bell_Details'] = ''

    # from the raw bell time, select the most often repeated bell configuration to represent the whole video
    config_dict = defaultdict(int)
    for i, v in df.loc[df['Type'] == 'Warning_Bell'].iterrows():
        before_type = df.loc[i - 1, 'Type']
        after_type = df.loc[i + 1, 'Type']

        if before_type == 'Start':
            continue

        if after_type == 'End':
            continue

        if before_type == 'Bell' and df.loc[i, 'half_min'] in [3, 5]:
            df.loc[i - 1, 'Bell_Details'] = 'Start'

        if after_type == 'Bell' and df.loc[i + 1, 'half_min'] == 1:
            df.loc[i + 1, 'Bell_Details'] = 'End'

        df.loc[i, 'Bell_Details'] = 'Warning'

        config_key = "_".join(map(str, df.loc[i - 1:i + 1, 'half_min'].to_list()))
        config_dict[config_key] += 1
    # select the most repeated configuration as final
    final_config = max(config_dict, key=config_dict.get)
    config_df = pd.DataFrame()
    config_df.loc[:, 'half_min_config'] = list(map(int, final_config.split('_')))
    config_df.loc[:, 'Bell_Details'] = ('Start', 'Warning', 'End')
    df = pd.merge(df, config_df, how='left', on='Bell_Details')
    df.loc[:, 'Diff'] = df['half_min_config'] - df['half_min']

    # if bell before Warning_Bell and if delta is 1.5min or 2.5 min then bell is Start Bell
    # if bell after Warning_Bell and if delta is 30, then bell is End Bell
    # A round consists of Start Bell, Warning_Bell, End_Bell
    # After End_Bell, either 30 sec or 60 sec for Start Bell

    for i, v in df.loc[df['Diff'] < 0, :].iterrows():
        curr_bell = v['Bell_Details']
        curr_second = v['Seconds']
        diff = v['Diff']
        new_slice = pd.DataFrame()
        new_type = ''
        if curr_bell == 'Warning':
            # adding a missing Start Bell
            new_type = 'Start'
        elif curr_bell == 'Start':
            new_type = 'End'
        elif curr_bell == 'End':
            new_type = 'Warning'

        new_slice = pd.DataFrame(
            {'Type': ['Fixed_Bell'], 'Seconds': [curr_second + diff * 30], 'Delta': [-1 * diff * 30],
             'Bell_Details': [new_type]})

        # Fix curr slice
        df.loc[i, 'Delta'] += diff * 30
        df.loc[i, 'half_min'] += diff
        df.loc[i, 'Diff'] = 0

        # insert by adding to end
        df = pd.concat([df, new_slice])

    # sort by Seconds to fix index
    df = df.sort_values('Seconds').reset_index(drop=True)
    df = df.drop(columns=['half_min', 'half_min_config', 'Diff'])
    # select data with just rounds
    df = df.loc[
         df.loc[df['Bell_Details'] == 'Start', :].index.min():df.loc[df['Bell_Details'] == 'End', :].index.max(), ]
    # Count rounds
    df.loc[:, 'Round'] = 0
    df.loc[df['Bell_Details'] == 'Start', 'Round'] = 1
    df.loc[:, 'Round'] = df['Round'].cumsum()
    # fix missing format
    for idx in df.loc[df['Formatted_Time'].isna(),:].index.to_list():
        df.loc[idx,'Formatted_Time'] = fmt_time(int(df.loc[idx,'Seconds']))

    df = df.loc[:,['Round','Formatted_Time','Bell_Details','Delta']]
    df = df.rename(columns={'Formatted_Time':'TimeStamp','Bell_Details':'BellType','Delta':'SecondsFromLastBell'})
    return df


if __name__ == "__main__":
    #mp3_file_path = os.path.join(base_dir, 'input','audio_sample.mp3')
    mp3_file_path = os.path.join(base_dir, 'input', 'audio.mp3')

    audio = BoxingAudio(mp3_file_path)
    audio.main()