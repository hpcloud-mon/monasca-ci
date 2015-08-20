#!/opt/monasca/bin/python
#
from __future__ import print_function
import argparse
import kafka
import glob
import MySQLdb
from monascaclient import ksclient
import psutil
import requests
import shlex
import smoke2_configs
import socket
import subprocess
import sys

config = smoke2_configs.test_config
args = 0
success = True

# successfully = '\033[5;40;32mSuccessfully\033[0m'
# successful = '\033[5;40;32mSuccessful.\033[0m'
# error = '\033[5;41;37m[ERROR]:\033[0m'
successfully = 'Successfully'
successful = 'Successful.'
error = '[ERROR]'

# parse command line arguments
def parse_commandline_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-dbtype', '--dbtype',
                        default=config['default']['arg_defaults']['dbtype'],
                        help='specify which database (influxdb or vertica)')
    parser.add_argument('-k', '--kafka',
                        default=config['default']['arg_defaults']['kafka'],
                        help='will check kafka on listed node(s). '
                             'ex. -k "192.168.10.4,192.168.10.7"')
    parser.add_argument('-z', '--zoo',
                        default=config['default']['arg_defaults']['zoo'],
                        help='will check zookeeper on listed node(s). '
                             'ex. -z "192.168.10.4,192.168.10.7"')
    parser.add_argument('-m', '--mysql',
                        default=config['default']['arg_defaults']['mysql'],
                        help='will check mysql on listed node. '
                             'ex. -m "192.168.10.4"')
    parser.add_argument('-db', '--db',
                        help='will check database on listed node. '
                             'ex. -db "192.168.10.4"')
    parser.add_argument('-s', '--single',
                        help='will check all services on single node. '
                             'ex. -s "192.168.10.4"')
    parser.add_argument('-api', '--monapi',
                        default=config['default']['arg_defaults']['monapi'],
                        help='will check url api access on node. '
                             'ex. -api "192.168.10.4"')
    parser.add_argument('-v', '--verbose', action='store_true', default=0,
                        help='will display all checking info')
    return parser.parse_args()


def find_processes():
    global success
    """Find_process is meant to validate that all the required processes
    are running"""
    process_missing = []
    process_list = config['default']['check']['expected_processes']

    for process in process_list:
        process_found_flag = False

        for item in psutil.process_iter():
            for cmd in item.cmdline():
                if process in cmd:
                    process_found_flag = True
                    break

        if not process_found_flag:
            process_missing.append(process)

    if len(process_missing) > 0:   # if processes were not found
        print (error + ' Process = {} Not Found'
               .format(process_missing))
        success = False
    else:
        print(successful + ' All Processes are running.')


def check_port(node, port):
    """Returns False if port is open (for fail check)"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((node, port))
    if result == 0:
        if args.verbose:
            print(successful + " Port {} is open".format(port))
        return False
    else:
        print(error + " Port {0} is not open on node {1}".format(port,node))
        return True


def debug_kafka(node):
    global success
    print('********VERIFYING KAFKA NODE(S)********')
    node = node.split(',')
    topics = config['default']['kafka']['topics']
    cluster_status = True
    for nodeip in node:
        if nodeip[-5:-4] == ':':
            nodeip = nodeip[:-5]
        fail = check_port(nodeip, 9092)
        if fail:
            cluster_status = False
            continue
        if args.verbose:
            print('Checking topics on node {}:'.format(nodeip))
        kafka_client = kafka.client.KafkaClient(nodeip + ':9092')
        for topic in topics:
            try:
                kafka.consumer.SimpleConsumer(
                    kafka_client,
                    'Foo',
                    topic,
                    auto_commit=True,
                    max_buffer_size=None)
                if args.verbose:
                    print('\t' + successfully + ' connected '
                                                'to topic {}'.format(topic))
            except KeyError:
                print('\t' + error + ' Could not connect '
                      'to topic {}'.format(topic))
                cluster_status = False
    if not cluster_status:
        success = False
    else:
        print(successful)


def debug_zookeeper(node):
    global success
    print('*******VERIFYING ZOOKEEPER NODE(S)*******')
    node = node.split(',')
    cluster_status = True
    for nodeip in node:
        if nodeip[-5:-4] == ':':
            nodeip = nodeip[:-5]
        fail = check_port(nodeip, 2181)
        if fail:
            cluster_status = False
            continue
        cmd = "nc " + nodeip + ' 2181'
        ps = subprocess.Popen(('echo', 'ruok'), stdout=subprocess.PIPE)
        try:
            output = subprocess.check_output(shlex.split(cmd),
                                             stdin=ps.stdout)
            if output == 'imok':
                if args.verbose:
                    print("cmd: echo ruok | " + cmd + " Response: {}"
                          .format(output) + " " + successful)
        except subprocess.CalledProcessError:
            print(error + ' Node {} is not responding'.format(nodeip))
            cluster_status = False
    if not cluster_status:
        success = False
    else:
        print(successful)


def debug_mysql(node, mysql_user, mysql_pass):
    global success
    print('********VERIFYING MYSQL NODE********')
    nodes = node.split(",")
    cluster_status = True
    for node in nodes:
        fail = check_port(node, 3306)
        if fail:
            cluster_status = False
            continue
        schema = config['default']['mysql_schema']
        try:
            conn = MySQLdb.connect(
                host=node,
                user=mysql_user,
                passwd=mysql_pass,
                db='mon')
            if args.verbose:
                print(successfully + ' connected to node {}'.format(node))
            conn.query('show tables')
            result = conn.store_result()
            if args.verbose:
                print('Checking MYSQL Table Schema on node {}:'.format(node))
            for x in range(0, result.num_rows()):
                row = result.fetch_row()[0][0]
                if row in schema:
                    if args.verbose:
                        print('\t' + successfully +
                              ' matched table {}'.format(row))
                else:
                    print('\t' + error + ' Table {} does not '
                          'match config'.format(row))
                    cluster_status = False
        except MySQLdb.OperationalError, e:
            print(error + ' MySQL connection failed: {0} on node {1}'.format(e, node))
            cluster_status = False
    if not cluster_status:
        success = False
    else:
        print(successful)


def debug_influx(node, influx_user, influx_pass):
    global success
    print('********VERIFYING INFLUXDB NODE********')
    try:
        from influxdb import client
    except ImportError:
        print("[WARNING]: InfluxDB Python Package is not installed!")
        return 1
    fail = check_port(node, 8086)
    fail |= check_port(node, 8090)
    if fail:
        success = False
    try:
        conn = client.InfluxDBClient(
            node,
            8086,
            influx_user,
            influx_pass,
            'mon'
        )
        conn.query('show series;')
        if args.verbose:
            print(successfully + ' connected to node {}'.format(node))
        else:
            print(successful)
    except Exception, e:
        print('{}'.format(e))
        success = False


def debug_vertica():
    global success
    print('********VERIFYING VERTICA NODE********')
    try:
        cmd = "sudo su dbadmin -c '/opt/vertica/bin/admintools -t view_cluster'"
        output = subprocess.check_output(shlex.split(cmd))
        if args.verbose:
            print("Running cmd: admintools -t view_cluster -d mon as user dbadmin")
            print("Response: " + output)
        if "DOWN" in output:
            print(error + " Part of the cluster is DOWN: \n{0}".format(output))
            success = False
        else:
            print(successful)
    except subprocess.CalledProcessError:
        print(error + " Cannot connect to vertica")
        success = False


def debug_keystone(key_user, key_pass, project, auth_url):
    keystone = {
        'username': key_user,
        'password': key_pass,
        'project': project,
        'auth_url': auth_url
    }
    ks_client = ksclient.KSClient(**keystone)
    if args.verbose:
        print(successfully + ' connected to keystone with '
                             'token {}'.format(ks_client.token))
    else:
        print(successful)
    return ks_client.token


def debug_rest_urls(node, token):
    global success
    print('********VERIFYING REST API********')
    nodes = node.split(",")
    cluster_status = True
    for node in nodes:
        url = 'http://' + node + ":8070/"
        fail = check_port(node, 8070)
        if fail:
            cluster_status = False
            continue
        try:
            r = requests.request("GET", url, headers={'X-Auth-Token': token})
            if r.status_code == 200:
                version_id = r.json()['elements'][0]['id']
                if args.verbose:
                    print(successfully + ' connected to REST API on '
                                         'node {}. Response (version id): {}'
                          .format(node, version_id))
            else:
                print(error + ' unexpected response received: \n'
                              '{}'.format(r.text))
                cluster_status = False
        except requests.ConnectionError as e:
            print(error + ' connection error received from node {}'.format(node))
            print("\t {}".format(e))
            cluster_status = False
        except Exception as e:
            print(error + ' error received from node {}'.format(node))
            print("\t {}".format(e))
            cluster_status = False
    if not cluster_status:
        success = False
    else:
        print(successful)


def debug_storm(node):
    global success
    print('********VERIFYING STORM********')
    cmd = "/opt/storm/apache*"
    cmd = glob.glob(cmd)[0] + "/bin/storm list"
    grep = "grep 'ACTIVE'"
    try:
        ps = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
        output = subprocess.check_output(shlex.split(grep), stdin=ps.stdout)
        if output:
            output = output[:27]
            output = " ".join(output.split())
            if args.verbose:
                print(successful + " Storm status: {}".format(output))
            else:
                print(successful)
    except Exception, e:
        print(error + " {}".format(e))
        success = False


def stage_one(single=None, zoo=None, kafka=None):
    global success
    if single:
        debug_zookeeper(single)
    elif zoo:
        debug_zookeeper(zoo)
    else:
        print(error + ' Could not parse zookeeper node!')
        success = False

    if single:
        debug_kafka(single)
    elif kafka:
        debug_kafka(kafka)
    else:
        print(error + ' Could not parse kafka node!')
        success = False


def stage_two(single=None, mysql=None, dbtype=None, db=None):
    global success
    mysql_user = config['mysql']['user']
    mysql_pass = config['mysql']['pass']
    if mysql_user and mysql_pass:
        if single:
            debug_mysql(single, mysql_user, mysql_pass)
        elif mysql:
            debug_mysql(mysql, mysql_user, mysql_pass)
        else:
            print(error + ' Could not parse node for mysql')
            success = False
    else:
        print(error + ' Could not parse mysql user/pass')
        success = False

    if dbtype == 'vertica':
        debug_vertica()
    else:
        influx_user = config['influx']['user']
        influx_pass = config['influx']['pass']
        influx_node = config['influx']['node']
        if single:
            debug_influx(single, influx_user, influx_pass)
        else:
            if db:
                debug_influx(db, influx_user, influx_pass)
            elif influx_node:
                if influx_node[0] == 'h':
                    influx_node = influx_node[7:-5]
                    debug_influx(influx_node, influx_user, influx_pass)
                else:
                    debug_influx(influx_node, influx_user, influx_pass)
            else:
                print(error + " Could not parse influxdb node")
                success = False


def stage_three(single=None, monapi=None):
    global success
    print('*****VERIFYING KEYSTONE*****')
    key_user = config['keystone']['user']
    key_pass = config['keystone']['pass']
    key_host = config['keystone']['host']
    if key_host:
        auth_url = "http://" + key_host + ':35357/v3'
        if key_user and key_pass:
            try:
                token = debug_keystone(key_user, key_pass, 'test', auth_url)
            except Exception, e:
                print(error + ' {}'.format(e))
                success = False
        else:
            print(error + ' Could not parse keystone user/pass')
            success = False
    else:
        print(error + ' Could not parse keystone node')
        success = False

    if single:
        debug_rest_urls(single, token)
    elif monapi:
        debug_rest_urls(monapi, token)
    else:
        print(error + ' Could not parse node for REST API')
        success = False

    storm_node = config['storm']
    if storm_node:
        debug_storm(storm_node)
    else:
        print(error + ' Could not parse storm node')
        success = False


def main():
    # parse the command line arguments
    global args
    args = parse_commandline_args()

    # Stage One
    # Will check Zookeeper and Kafka
    stage_one(args.single, args.zoo, args.kafka)

    print('*****VERIFYING HOST SERVICES/PROCESSES*****')
    find_processes()

    # Stage Two
    # Will check MySQL and vertica/influxdb
    stage_two(args.single, args.mysql, args.dbtype, args.db)

    # Stage Three
    # Will check keystone, REST API, and Storm
    stage_three(args.single, args.monapi)

    if not success:
        print('*****TESTS FAILED*****')
        return 1

    print('*****TESTS SUCCEEDED*****')
    return 0

if __name__ == "__main__":
    sys.exit(main())
